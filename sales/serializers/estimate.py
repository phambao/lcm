import re
import random

from django.db import IntegrityError
from django.apps import apps
from django.db.models import Sum
from django.contrib.contenttypes.models import ContentType
from django.db.utils import DataError
from django.urls import reverse
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from api.middleware import get_request
from base.serializers.base import IDAndNameSerializer
from base.constants import true, null, false
from base.tasks import activity_log
from base.utils import pop, extra_kwargs_for_base_model
from sales.models import DataPoint, Catalog
from sales.models.estimate import POFormula, POFormulaGrouping, DataEntry, POFormulaToDataEntry, RoundUpActionChoice, RoundUpChoice, \
    UnitLibrary, DescriptionLibrary, Assemble, EstimateTemplate, DataView, MaterialView, GroupTemplate
from sales.serializers import ContentTypeSerializerMixin
from sales.serializers.catalog import CatalogEstimateSerializer, DataPointForLinkDescription


class LinkedDescriptionSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    linked_description = serializers.CharField()

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['id'] = str(data['id'])
        if isinstance(instance, DescriptionLibrary):
            data['id'] = 'estimate:' + data['id']
            data['name'] = instance.name
        else:
            data['id'] = 'catalog:' + data['id']
            data['name'] = instance.catalog.name + '-' + str(instance.pk)
        return data


class DataEntrySerializer(ContentTypeSerializerMixin):
    unit = IDAndNameSerializer(required=False, allow_null=True)
    material_selections = CatalogEstimateSerializer('data_entries', many=True, required=False, allow_null=True)

    class Meta:
        model = DataEntry
        fields = ('id', 'name', 'unit', 'dropdown', 'is_dropdown', 'is_material_selection', 'material_selections',
                  'created_date', 'modified_date', 'levels', 'material', 'default_column')
        extra_kwargs = {'id': {'read_only': False, 'required': False}}
        read_only_fields = ('created_date', 'modified_date')

    def validate_name(self, value):
        from sales.views.estimate import DataEntryList, DataEntryDetail
        request = get_request()
        queryset = DataEntry.objects.filter(company=request.user.company)
        view = self.context.get('view', None)
        if isinstance(view, DataEntryList) or isinstance(view, DataEntryDetail):
            if self.instance:
                queryset = queryset.exclude(id=self.instance.id)

            if queryset.filter(name=value).exists():
                raise serializers.ValidationError("The name is already taken, please choose another name.")

            if re.search(r'[\[\]\(\)]', value):
                raise serializers.ValidationError(
                    "The name cannot contain characters like ']', '[' , ')', '(' . Please choose another name.")
        return value

    def set_material(self, material_selections):
        catalog_pks = []
        for material_selection in material_selections:
            catalog_pks.append(material_selection.get('id'))
        catalogs = Catalog.objects.filter(pk__in=catalog_pks)
        return catalogs

    def create(self, validated_data):
        unit = pop(validated_data, 'unit', {})
        material_selections = pop(validated_data, 'material_selections', {})
        validated_data['unit_id'] = unit.get('id', None)
        instance = super().create(validated_data)

        catalogs = self.set_material(material_selections)
        instance.material_selections.add(*catalogs)

        from sales.views.estimate import DataEntryList
        if isinstance(self.context.get('view'), DataEntryList):
            activity_log.delay(instance.get_content_type().pk, instance.pk, 1,
                               DataEntrySerializer.__name__, __name__, self.context['request'].user.pk)
        return instance

    def update(self, instance, validated_data):
        unit = pop(validated_data, 'unit', {})
        material_selections = pop(validated_data, 'material_selections', {})

        instance.material_selections.clear()
        catalogs = self.set_material(material_selections)
        instance.material_selections.add(*catalogs)

        validated_data['unit_id'] = unit.get('id', None)
        new_name = validated_data['name']
        old_name = instance.name
        update = super().update(instance, validated_data)
        # Update all data entry mentioned on formula
        if new_name != old_name:
            objs = POFormulaToDataEntry.objects.filter(
                data_entry=instance, po_formula__isnull=False
            ).select_related('po_formula')
            data = []
            for obj in objs:
                obj = obj.po_formula
                obj.formula = obj.formula.replace(old_name, new_name)
                obj.formula_mentions = obj.formula_mentions.replace(old_name, new_name)
                data.append(obj)
            POFormula.objects.bulk_update(data, ['formula', 'formula_mentions'], batch_size=128)

        activity_log.delay(instance.get_content_type().pk, instance.pk, 2,
                           DataEntrySerializer.__name__, __name__, self.context['request'].user.pk)
        return update

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['catalog'] = {}
        data['category'] = {}
        if data['material_selections']:
            parent = Catalog.objects.get(pk=data['material_selections'][0].get('id'))
            parent = parent.parents.first()
            data['category'] = CatalogEstimateSerializer(parent).data
            parent = parent.parents.first()
            data['catalog'] = CatalogEstimateSerializer(parent).data

        if data['levels']:
            for level in data['levels']:
                try:
                    c = Catalog.objects.get(pk=level.get('id'))
                    level['data_points'] = DataPointForLinkDescription(c.data_points.all(), many=True).data
                except (Catalog.DoesNotExist, ValueError):
                    level['data_points'] = []
        return data


class POFormulaToDataEntrySerializer(serializers.ModelSerializer):
    data_entry = DataEntrySerializer(allow_null=True, required=False)

    class Meta:
        model = POFormulaToDataEntry
        fields = ('id', 'value', 'data_entry', 'index', 'dropdown_value', 'material_value', 'nick_name',
                  'copies_from', 'group', 'material_data_entry_link', 'levels', 'is_client_view', 
                  'po_group_index', 'po_index', 'custom_group_name', 'custom_group_index', 'custom_index',
                  'custom_po_index', 'is_lock_estimate', 'is_lock_proposal', 'is_press_enter',
                  'default_value', 'default_dropdown_value', 'default_material_value')

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if not data['nick_name']:
            data['nick_name'] = instance.data_entry.name
        data['po_group_name'] = instance.get_po_group_name()
        return data


def create_po_formula_to_data_entry(instance, data_entries, estimate_id=None, change_default=False):
    data = []
    for data_entry in data_entries:
        params = {"po_formula_id": instance.pk, "value": data_entry['value'], 'index': data_entry.get('index'),
                  'dropdown_value': data_entry.get('dropdown_value', ''), 'estimate_template_id': estimate_id,
                  'material_value': data_entry.get('material_value', ''), 'copies_from': data_entry.get('copies_from'),
                  'group': data_entry.get('group', ''), 'material_data_entry_link': data_entry.get('material_data_entry_link'),
                  'levels': data_entry.get('levels', []), 'is_client_view': data_entry.get('is_client_view', True),
                  'nick_name': data_entry.get('nick_name', ''), 'po_group_index': data_entry.get('po_group_index'),
                  'po_index': data_entry.get('po_index'), 'custom_group_name': data_entry.get('custom_group_name') or '',
                  'custom_group_index': data_entry.get('custom_group_index'), 'custom_index': data_entry.get('custom_index'),
                  'custom_po_index': data_entry.get('custom_po_index'), 'is_lock_estimate': data_entry.get('is_lock_estimate') or False,
                  'is_lock_proposal': data_entry.get('is_lock_proposal') or False, 'is_press_enter': data_entry.get('is_press_enter') or False,
                  'default_value': data_entry.get('default_value') or '', 'default_dropdown_value': data_entry.get('default_dropdown_value') or {},
                  'default_material_value': data_entry.get('default_material_value') or {}}
        if change_default:
            params['default_value'] = data_entry.get('value') or ''
            params['default_dropdown_value'] = data_entry.get('dropdown_value') or {}
            params['default_material_value'] = data_entry.get('material_value') or {}
        try:
            data_entry_pk = data_entry.get('data_entry', {}).get('id', None)
            if data_entry_pk:
                params["data_entry_id"] = data_entry_pk
            else:
                data_entry_params = data_entry.get('data_entry', {})
                unit = pop(data_entry_params, 'unit', {})
                data_entry_params['unit_id'] = unit.get('id')
                params["data_entry_id"] = DataEntry.objects.create(**data_entry_params).pk
            data.append(POFormulaToDataEntry(**params))
        except KeyError:
            pass
    POFormulaToDataEntry.objects.bulk_create(data)


class POFormulaForInvoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = POFormula
        fields = ('id', 'name', 'total_cost', 'charge', 'cost', 'unit_price', 'quantity')

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['unit'] = 'USD'
        data['invoice_overview'] = 0
        data['cost_type'] = []
        return data


class POFormulaDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = POFormula
        fields = ('id', 'name', 'markup', 'charge', 'material', 'unit',
                  'unit_price', 'cost', 'total_cost', 'gross_profit', 'description_of_formula', 'formula_scenario',
                  'material_data_entry', 'formula_for_data_view', 'order')


class POFormulaCompactSerializer(serializers.ModelSerializer):

    class Meta:
        model = POFormula
        exclude = ('material', 'formula_mentions', 'formula_data_mentions', 'description_of_formula', 'assemble', 'order',
                   'formula_scenario', 'formula_for_data_view', 'original', 'catalog_materials', 'company', 'created_from')

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data_entry_ids = self.context['request'].GET.getlist('data_entry')
        data['group_by'] = DataEntry.objects.filter(
            id__in=data_entry_ids, poformulatodataentry__po_formula=instance
        ).distinct().values('id', 'name')
        return data


class RoundUPSeriailzer(serializers.Serializer):
    type = serializers.ChoiceField(choices=RoundUpChoice.choices, required=False, allow_null=True)
    whole_number = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    increments = serializers.ListField(required=False, allow_null=True)
    last_action = serializers.ChoiceField(choices=RoundUpActionChoice, required=False, allow_null=True)
    action_value = serializers.IntegerField(required=False, allow_null=True)


class POFormulaSerializer(ContentTypeSerializerMixin):
    self_data_entries = POFormulaToDataEntrySerializer('po_formula', many=True, required=False, read_only=False)
    round_up = RoundUPSeriailzer(allow_null=True, required=False)

    class Meta:
        model = POFormula
        fields = '__all__'
        extra_kwargs = {**{'id': {'read_only': False, 'required': False}}, **extra_kwargs_for_base_model()}
        read_only_fields = ('assemble', 'group')

    def create(self, validated_data):
        data_entries = pop(validated_data, 'self_data_entries', [])
        pop(validated_data, 'id', None)
        instance = super().create(validated_data)
        create_po_formula_to_data_entry(instance, data_entries)

        from sales.views.estimate import POFormulaList
        if isinstance(self.context.get('view'), POFormulaList):
            activity_log.delay(instance.get_content_type().pk, instance.pk, 1,
                               POFormulaSerializer.__name__, __name__, self.context['request'].user.pk)
        return instance

    def update(self, instance, validated_data):
        data_entries = pop(validated_data, 'self_data_entries', [])
        instance.self_data_entries.all().delete()
        create_po_formula_to_data_entry(instance, data_entries)
        activity_log.delay(instance.get_content_type().pk, instance.pk, 2,
                           POFormulaSerializer.__name__, __name__, self.context['request'].user.pk)
        new_name = validated_data['name']
        old_name = instance.name
        update = super().update(instance, validated_data)
        # Update all formula mentioned on this formula
        if new_name != old_name:
            company = self.context.get('request').user.company
            data = []
            objs = POFormula.objects.filter(company=company, formula__icontains=old_name)
            for obj in objs:
                obj.formula = obj.formula.replace(old_name, new_name)
                obj.formula_mentions = obj.formula_mentions.replace(old_name, new_name)
                data.append(obj)
            POFormula.objects.bulk_update(data, ['formula', 'formula_mentions'], batch_size=128)
        return update

    def validate_material(self, value):
        if value:
            try:
                parsed_value = eval(value)
                if not isinstance(parsed_value, dict):
                    raise serializers.ValidationError("material is not valid")
            except:
                raise serializers.ValidationError("material is not valid")
        return value

    def validate_material_data_entry(self, value):
        if value:
            serializer = POFormulaToDataEntrySerializer(data=value)
            serializer.is_valid(raise_exception=True)
        return value

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if data['material']:
            try:
                primary_key = eval(data['material'])
                pk_catalog, row_index = primary_key.get('id').split(':')
                catalog = Catalog.objects.get(pk=pk_catalog)
                ancestors = catalog.get_full_ancestor()
                ancestor = ancestors[-1]
                data['catalog_ancestor'] = ancestor.pk
                data['catalog_link'] = [CatalogEstimateSerializer(c).data for c in ancestors[::-1]]
                if primary_key and isinstance(primary_key, dict):
                    primary_key.update(catalog.get_material(primary_key.get('id')))
                    primary_key.update({'levels': data['catalog_link']})
                    data['material_value'] = primary_key
                data['catalog_materials'] = data['catalog_link']
            except (Catalog.DoesNotExist, IndexError, NameError, SyntaxError, AttributeError):
                data['catalog_ancestor'] = None
                data['catalog_link'] = []
                data['material_value'] = {}
        else:
            data['catalog_materials'] = [i for i in data['catalog_materials'] if i]
            data['material_value'] = {}
            data['catalog_ancestor'] = None
            data['catalog_link'] = []

        if not instance.round_up:
            data['round_up'] = None

        original = data.get('original')
        if not original:
            data['original'] = instance.pk

        data['status'] = instance.status()
        return data


class GroupFormulasSerializer(serializers.ModelSerializer):
    group_formulas = serializers.PrimaryKeyRelatedField(queryset=POFormula.objects.all(), many=True, allow_null=True, required=False)

    class Meta:
        model = POFormulaGrouping
        fields = ('id', 'name', 'group_formulas')

    def create(self, validated_data):
        group_formulas = pop(validated_data, 'group_formulas', [])
        instance = super().create(validated_data)
        for formula in group_formulas:
            formula.group = instance
            formula.save()
        return instance


class POFormulaGroupCompactSerializer(serializers.ModelSerializer):

    class Meta:
        model = POFormulaGrouping
        fields = ('id', 'name')


class POFormulaGroupingSerializer(serializers.ModelSerializer):
    group_formulas = POFormulaSerializer('group', many=True, allow_null=True, required=False)

    class Meta:
        model = POFormulaGrouping
        fields = ('id', 'name', 'group_formulas')

    def add_relation_po_formula(self, po_formulas, instance):
        po_pk = []
        for po_formula in po_formulas:
            pk = po_formula.get('id', None)
            if pk:
                po_pk.append(pk)
            else:
                po = POFormulaSerializer(data=po_formula)
                po.is_valid(raise_exception=True)
                po.save(is_show=True, group=instance)
        return po_pk

    def create(self, validated_data):
        po_formulas = pop(validated_data, 'group_formulas', [])
        instance = super().create(validated_data)
        po_pk = self.add_relation_po_formula(po_formulas, instance)
        POFormula.objects.filter(id__in=po_pk, group=None).update(group=instance)
        return instance

    def update(self, instance, validated_data):
        po_formulas = pop(validated_data, 'group_formulas', [])
        method = self.context.get('request').method
        if (method == 'PATCH' and po_formulas) or method == 'PUT':
            instance.group_formulas.all().update(group=None)
            po_pk = self.add_relation_po_formula(po_formulas, instance)
            POFormula.objects.filter(id__in=po_pk, group=None).update(group=instance)
        return super(POFormulaGroupingSerializer, self).update(instance, validated_data)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['content_type'] = ContentType.objects.get_for_model(POFormulaGrouping).pk
        return data


class UnitLibrarySerializer(ContentTypeSerializerMixin):
    class Meta:
        model = UnitLibrary
        fields = ('id', 'name', 'description', 'created_date', 'modified_date', 'user_create', 'user_update')
        read_only_fields = ('created_date', 'modified_date', 'user_create', 'user_update')

    def create(self, validated_data):
        try:
            instance = super().create(validated_data)
        except IntegrityError:
            raise serializers.ValidationError({'name': 'name is duplicated'})

        from sales.views.estimate import UnitLibraryList
        if isinstance(self.context.get('view'), UnitLibraryList):
            activity_log.delay(instance.get_content_type().pk, instance.pk, 1,
                               UnitLibrarySerializer.__name__, __name__, self.context['request'].user.pk)
        return instance

    def update(self, instance, validated_data):
        old_name = instance.name
        try:
            obj = super().update(instance, validated_data)
        except IntegrityError:
            raise serializers.ValidationError({'name': 'name is duplicated'})
        activity_log.delay(instance.get_content_type().pk, instance.pk, 2,
                           UnitLibrarySerializer.__name__, __name__, self.context['request'].user.pk)
        catalogs = instance.get_related_cost_table(old_name)
        cs = []
        for c in catalogs:
            c.c_table, have_changed = c.update_unit_c_table(old_name, validated_data.get('name'))
            if have_changed:
                cs.append(c)
        model = apps.get_model(app_label='sales', model_name='Catalog')
        model.objects.bulk_update(cs, ['c_table'])
        return obj


class DescriptionLibrarySerializer(ContentTypeSerializerMixin):
    class Meta:
        model = DescriptionLibrary
        fields = ('id', 'name', 'linked_description', 'created_date', 'modified_date')
        read_only_fields = ('created_date', 'modified_date')

    def create(self, validated_data):
        instance = super().create(validated_data)

        from sales.views.estimate import DescriptionLibraryList
        if isinstance(self.context.get('view'), DescriptionLibraryList):
            activity_log.delay(instance.get_content_type().pk, instance.pk, 1,
                               DescriptionLibrarySerializer.__name__, __name__, self.context['request'].user.pk)
        return instance

    def update(self, instance, validated_data):
        activity_log.delay(instance.get_content_type().pk, instance.pk, 2,
                           DescriptionLibrarySerializer.__name__, __name__, self.context['request'].user.pk)
        return super().update(instance, validated_data)


class AssembleCompactSerializer(serializers.ModelSerializer):

    class Meta:
        model = Assemble
        fields = ('id', 'name', 'created_date', 'modified_date', 'user_create', 'user_update', 'description')

    def create(self, validated_data):
        raise ValidationError('Can not Create')

    def to_representation(self, instance):
        data = super().to_representation(instance)
        formula_ids = self.context['request'].GET.getlist('formula')
        related_formula = POFormula.objects.filter(original__in=formula_ids, assemble=instance).values_list('original')
        data['group_by'] = POFormula.objects.filter(pk__in=related_formula).distinct().values('id', 'name')
        return data


class AssembleSerializer(ContentTypeSerializerMixin):
    assemble_formulas = POFormulaSerializer('assemble', many=True, required=False, allow_null=True)

    class Meta:
        model = Assemble
        fields = ('id', 'name', 'created_date', 'modified_date', 'user_create', 'user_update',
                  'assemble_formulas', 'description', 'is_show', 'original', 'is_custom_assemble')
        extra_kwargs = extra_kwargs_for_base_model()

    def create_po_formula(self, po_formulas, instance):
        max_int = 2147483647
        for po_formula in po_formulas:
            if not po_formula.get('formula_for_data_view'):
                po_formula['formula_for_data_view'] = po_formula.get('id') if po_formula.get('id') < max_int else random.randint(1, 10000)
            old_pk = po_formula['id']
            del po_formula['id']
            po = POFormulaSerializer(data=po_formula, context=self.context)
            po.is_valid(raise_exception=True)
            formula = po.save(assemble=instance, is_show=False)
            new_pk = formula.id
            try:
                group = GroupTemplate.objects.filter(items__contains=[old_pk], is_formula=True)
                for g in group:
                    g.items.remove(old_pk)
                    g.items.append(new_pk)
                    g.save()
            except DataError:
                pass

    def create(self, validated_data):
        po_formulas = pop(validated_data, 'assemble_formulas', [])
        instance = super().create(validated_data)
        self.create_po_formula(po_formulas, instance)

        from sales.views.estimate import AssembleList
        if isinstance(self.context.get('view'), AssembleList):
            activity_log.delay(instance.get_content_type().pk, instance.pk, 1,
                               AssembleSerializer.__name__, __name__, self.context['request'].user.pk)
        return instance

    def update(self, instance, validated_data):
        po_formulas = pop(validated_data, 'assemble_formulas', [])
        instance.assemble_formulas.all().delete()
        self.create_po_formula(po_formulas, instance)
        activity_log.delay(instance.get_content_type().pk, instance.pk, 2,
                           AssembleSerializer.__name__, __name__, self.context['request'].user.pk)
        return super().update(instance, validated_data)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        original = data.get('original')
        if not original:
            data['original'] = instance.pk
        return data


class DataViewSerializer(serializers.ModelSerializer):
    unit = UnitLibrarySerializer(required=False, allow_null=True)
    class Meta:
        model = DataView
        fields = ('id', 'formula', 'name', 'estimate_template', 'type', 'is_client_view', 'unit', 'result')
        read_only_fields = ('estimate_template', )

    def create(self, validated_data):
        unit = pop(validated_data, 'unit', {})
        if unit:
            try:
                unit = UnitLibrary.objects.get(name=unit.get('name'), company=self.context['request'].user.company)
            except UnitLibrary.DoesNotExist:
                unit = None
            validated_data['unit'] = unit

        return super().create(validated_data)

    def to_internal_value(self, data):
        data = super().to_internal_value(data)
        return data


class MaterialViewSerializers(serializers.ModelSerializer):
    data_entry = serializers.IntegerField(allow_null=True, required=False)
    class Meta:
        model = MaterialView
        fields = ('id', 'name', 'material_value', 'copies_from', 'catalog_materials',
                  'levels', 'data_entry', 'is_client_view', 'default_column', 'custom_po_index',
                  'po_group_index', 'po_index', 'custom_group_name', 'custom_group_index', 'custom_index',
                  'is_lock_estimate', 'is_lock_proposal', 'is_press_enter', 'default_value', 'default_material_value',
                  'default_dropdown_value')

    def validate_data_entry(self, value):
        if value:
            try:
                DataEntry.objects.get(pk=value)
            except DataEntry.DoesNotExist:
                return None
        return value

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['po_group_name'] = instance.get_po_group_name()
        return data


class EstimateTemplateForFormattingSerializer(serializers.ModelSerializer):

    class Meta:
        model = EstimateTemplate
        fields = ('id', 'name', 'quantity', 'unit')

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['quantity'] = ''
        data['unit'] = ''
        if instance.unit:
            data['unit'] = instance.unit.name
        if instance.quantity:
            data['quantity'] = instance.quantity.get('name')
        data['total_charge'] = instance.get_formula().aggregate(
            total_charge=Sum('charge')
        ).get('total_charge')
        return data


class EstimateTemplateCompactSerializer(serializers.ModelSerializer):

    class Meta:
        model = EstimateTemplate
        exclude = ('is_show', 'original', 'order', 'assembles', 'group_by_proposal', 'company', 'is_checked')

    def to_representation(self, instance):
        data = super().to_representation(instance)
        assemble_ids = self.context['request'].GET.getlist('assemble')
        related_assembles = Assemble.objects.filter(estimate_templates=instance, original__in=assemble_ids).values_list('original')
        data['group_by'] = Assemble.objects.filter(pk__in=related_assembles).distinct().values('id', 'name')
        return data


class POFormulaItemSerializer(serializers.ModelSerializer):
    """
    Used for proposal formatting
    """

    class Meta:
        model = POFormula
        fields = (
            'id', 'name', 'linked_description', 'formula', 'quantity', 'markup', 'charge', 'material', 'unit',
            'unit_price', 'cost', 'total_cost', 'gross_profit', 'description_of_formula', 'formula_scenario', 'order'
        )

    def to_representation(self, instance):
        data = super().to_representation(instance)
        try:
            data['material'] = eval(data['material'])
        except SyntaxError:
            data['material'] = ''
        if data['material'] and isinstance(data['material'], dict):
            data['material'] = data['material'].get('name')
        return data


class EstimateTemplateMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = EstimateTemplate
        fields = ('id', 'name', 'order')

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['items'] = POFormulaItemSerializer(instance.get_formula(), context=self.context, many=True).data
        return data


class QuantityEstimateSerializer(IDAndNameSerializer):
    type = serializers.ChoiceField(
        choices=(('data_entry', 'Data Entry'), ('data_view', 'Data View'), ('po', 'Formula')),
        required=False, allow_null=True
    )


class EstimateTemplateSerializer(ContentTypeSerializerMixin):
    assembles = AssembleSerializer(many=True, required=False, allow_null=True,)
    data_views = DataViewSerializer('estimate_template', many=True, required=False, allow_null=True)
    data_entries = POFormulaToDataEntrySerializer('estimate_template', many=True, required=False, allow_null=True)
    material_views = MaterialViewSerializers('estimate_template', many=True, required=False, allow_null=True)
    quantity = QuantityEstimateSerializer(required=False, allow_null=True)
    unit = IDAndNameSerializer(required=False, allow_null=True)

    class Meta:
        model = EstimateTemplate
        fields = '__all__'
        extra_kwargs = {**{'id': {'read_only': False, 'required': False}}, **extra_kwargs_for_base_model()}
        read_only_fields = ('group_by_proposal', )

    def create_assembles(self, assembles):
        pk_assembles = []
        for assemble in assembles:
            serializer = AssembleSerializer(data=assemble, context=self.context)
            serializer.is_valid(raise_exception=True)
            obj = serializer.save(is_show=False)
            pk_assembles.append(obj.pk)
        return pk_assembles

    def create_data_view(self, data_views, instance):
        for data_view in data_views:
            data_view['estimate_template'] = instance.pk
            serializer = DataViewSerializer(data=data_view, context=self.context)
            serializer.is_valid(raise_exception=True)
            serializer.save(estimate_template_id=instance.pk)

    def create_material_view(self, material_views, instance, change_default=False):
        for data_view in material_views:
            data_view['estimate_template'] = instance.pk
            data_entry = pop(data_view, 'data_entry', None)
            if data_entry:
                try:
                    data_entry = DataEntry.objects.get(pk=data_entry)
                except DataEntry.DoesNotExist:
                    raise serializers.ValidationError('Data Entry is not exist')
            serializer = MaterialViewSerializers(data=data_view)
            serializer.is_valid(raise_exception=True)
            params = {
                'estimate_template_id': instance.pk,
                'data_entry': data_entry
            }
            if change_default:
                params['default_material_value'] = serializer.data
            serializer.save(**params)

    def create(self, validated_data):
        assembles = pop(validated_data, 'assembles', [])
        data_views = pop(validated_data, 'data_views', [])
        data_entries = pop(validated_data, 'data_entries', [])
        material_views = pop(validated_data, 'material_views', [])
        validated_data['unit_id'] = pop(validated_data, 'unit', {}).get('id')
        old_pk = pop(validated_data, 'id', None)

        pk_assembles = self.create_assembles(assembles)
        instance = super().create(validated_data)
        new_pk = instance.pk
        change_default = False
        if self.context.get('request').path == reverse('sales.estimate.list'):
            change_default = True
        create_po_formula_to_data_entry(EstimateTemplate(name='name'), data_entries, instance.pk, change_default)
        self.create_data_view(data_views, instance)
        self.create_material_view(material_views, instance, change_default)
        instance.assembles.add(*Assemble.objects.filter(pk__in=pk_assembles))
        try:
            group = GroupTemplate.objects.filter(items__contains=[old_pk], is_formula=False)
            for g in group:
                g.items.remove(old_pk)
                g.items.append(new_pk)
                g.save()
        except DataError:
            pass

        from sales.views.estimate import EstimateTemplateList
        if isinstance(self.context.get('view'), EstimateTemplateList):
            activity_log.delay(instance.get_content_type().pk, instance.pk, 1,
                               EstimateTemplateSerializer.__name__, __name__, self.context['request'].user.pk)
        return instance

    def update(self, instance, validated_data):
        assembles = pop(validated_data, 'assembles', [])
        data_views = pop(validated_data, 'data_views', [])
        data_entries = pop(validated_data, 'data_entries', [])
        material_views = pop(validated_data, 'material_views', [])
        validated_data['unit_id'] = pop(validated_data, 'unit', {}).get('id')
        pk = pop(validated_data, 'id', None)

        instance.data_entries.all().delete()
        change_default = False
        if self.context.get('request').path == reverse('sales.estimate.detail', kwargs={'pk': instance.pk}):
            change_default = True
        create_po_formula_to_data_entry(EstimateTemplate(name='name'), data_entries, instance.pk, change_default)
        pk_assembles = self.create_assembles(assembles)

        instance = super().update(instance, validated_data)
        instance.data_views.all().delete()
        self.create_data_view(data_views, instance)
        instance.material_views.all().delete()
        self.create_material_view(material_views, instance, change_default)

        instance.assembles.all().delete()
        instance.assembles.add(*Assemble.objects.filter(pk__in=pk_assembles))
        activity_log.delay(instance.get_content_type().pk, instance.pk, 2,
                           EstimateTemplateSerializer.__name__, __name__, self.context['request'].user.pk)
        return instance

    def validate_unit(self, value):
        if value:
            if UnitLibrary.objects.filter(pk=value.get('id')).exists():
                return value
        return {}

    def to_representation(self, instance):
        data = super().to_representation(instance)
        original = data.get('original')
        if not original:
            data['original'] = instance.pk
        return data


class TaggingSerializer(serializers.Serializer):
    """
    Tagging for PO formula or Data point in Catalog
    """
    id = serializers.IntegerField()

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if isinstance(instance, POFormula):
            data['display'] = instance.name
            data['value'] = instance.charge
            data['ancestors'] = [CatalogEstimateSerializer(c).data for c in instance.get_link_catalog_by_material()]
            data['self_data_entries'] = POFormulaToDataEntrySerializer(instance.self_data_entries.all(), many=True).data
            data['formula_mentions'] = instance.formula_mentions
            data['formula'] = instance.formula
        if isinstance(instance, DataPoint):
            data['display'] = instance.catalog.name
            if instance.unit:
                data['display'] = instance.unit.name
            data['value'] = instance.value
            ancestors = []
            try:
                ancestors = instance.catalog.get_full_ancestor()
            except IndexError:
                """If data point is in the first category's level"""
            data['ancestors'] = [CatalogEstimateSerializer(c).data for c in ancestors]
        return data


class EstimateTemplateForInvoiceSerializer(serializers.ModelSerializer):
    data_views = DataViewSerializer('estimate_template', many=True, required=False, allow_null=True)
    class Meta:
        model = EstimateTemplate
        fields = ('id', 'name', 'contract_description', 'data_views')

    def to_representation(self, instance):
        data = super().to_representation(instance)
        instance.get_info()
        data['total_prices'] = instance.get_total_prices()
        data['unit_cost'] = instance.get_unit_cost()
        data['total_cost'] = instance.get_total_cost()
        data['unit_price'] = instance.get_unit_price()
        data['quantity'] = instance.get_quantity()
        return data
a = {
    "id": 24415,
    "assembles": [
        {
            "id": 45636,
            "name": "testing for scott",
            "created_date": "2024-05-31T07:25:19.258844Z",
            "modified_date": "2024-05-31T07:25:19.258860Z",
            "user_create": 5,
            "user_update": null,
            "assemble_formulas": [
                {
                    "id": 85759,
                    "self_data_entries": [],
                    "round_up": {
                        "type": "whole_number",
                        "whole_number": null,
                        "increments": [],
                        "last_action": "none",
                        "action_value": null
                    },
                    "created_date": "2024-05-31T07:25:19.267251Z",
                    "modified_date": "2024-05-31T07:25:19.267266Z",
                    "name": "Testing for Scott",
                    "linked_description": [],
                    "formula": "1111",
                    "created_from": null,
                    "is_show": false,
                    "quantity": "1111",
                    "markup": null,
                    "charge": "0",
                    "material": "{}",
                    "unit": "",
                    "unit_price": "0",
                    "cost": "0",
                    "total_cost": "0",
                    "margin": null,
                    "formula_mentions": "1111",
                    "formula_data_mentions": "",
                    "gross_profit": "",
                    "description_of_formula": "",
                    "formula_scenario": "",
                    "material_data_entry": {},
                    "formula_for_data_view": 81219,
                    "original": 81219,
                    "catalog_materials": [
                        null
                    ],
                    "order": 0,
                    "default_column": {},
                    "order_quantity": "1111",
                    "selected_description": null,
                    "is_custom_po": false,
                    "user_create": 5,
                    "user_update": null,
                    "company": 1,
                    "group": null,
                    "assemble": 45636,
                    "content_type": 57,
                    "catalog_ancestor": null,
                    "catalog_link": [],
                    "material_value": {},
                    "status": true
                }
            ],
            "description": "",
            "is_show": false,
            "original": 42798,
            "is_custom_assemble": false,
            "content_type": 82
        },
        {
            "id": 45637,
            "name": "Using For 2 Onlu",
            "created_date": "2024-05-31T07:25:19.284672Z",
            "modified_date": "2024-05-31T07:25:19.284687Z",
            "user_create": 5,
            "user_update": null,
            "assemble_formulas": [
                {
                    "id": 85760,
                    "self_data_entries": [
                        {
                            "id": 168339,
                            "value": "12.00",
                            "data_entry": {
                                "id": 12,
                                "name": "Gold",
                                "unit": {
                                    "id": 12,
                                    "name": "Gold"
                                },
                                "dropdown": [
                                    {
                                        "name": "",
                                        "value": ""
                                    }
                                ],
                                "is_dropdown": false,
                                "is_material_selection": false,
                                "material_selections": [],
                                "created_date": "2023-06-16T07:02:37.498000Z",
                                "modified_date": "2023-06-16T07:02:37.498000Z",
                                "levels": [],
                                "material": {},
                                "default_column": {
                                    "name": "cost",
                                    "value": 0
                                },
                                "content_type": 75,
                                "catalog": {},
                                "category": {}
                            },
                            "index": null,
                            "dropdown_value": {},
                            "material_value": {},
                            "nick_name": "Gold",
                            "copies_from": null,
                            "group": "",
                            "material_data_entry_link": null,
                            "levels": [],
                            "is_client_view": true,
                            "po_group_index": 0,
                            "po_index": 0,
                            "custom_group_name": "Default",
                            "custom_group_index": 0,
                            "custom_index": 0,
                            "custom_po_index": 0,
                            "is_lock_estimate": false,
                            "is_lock_proposal": false,
                            "is_press_enter": false,
                            "default_value": "",
                            "default_dropdown_value": {},
                            "default_material_value": {},
                            "po_group_name": "For 2 1"
                        }
                    ],
                    "round_up": {
                        "type": "whole_number",
                        "whole_number": null,
                        "increments": [],
                        "last_action": "none",
                        "action_value": null
                    },
                    "created_date": "2024-05-31T07:25:19.297178Z",
                    "modified_date": "2024-05-31T07:25:19.297193Z",
                    "name": "For 2 1",
                    "linked_description": [],
                    "formula": "Gold + 3",
                    "created_from": null,
                    "is_show": false,
                    "quantity": "15",
                    "markup": null,
                    "charge": "0",
                    "material": "{\"name\":\"UPS - all size\",\"unit\":\"kg\",\"cost\":\"20\",\"id\":\"50897:0\",\"levels\":[{\"id\":50887,\"name\":\"cong catalog\",\"level\":null,\"level_index\":0},{\"id\":50896,\"name\":\"Shiping Cost\",\"level\":null,\"level_index\":0},{\"id\":50897,\"name\":\"Singapore\",\"level\":1692,\"level_index\":0}],\"columns\":[{\"name\":\"name\",\"value\":\"UPS - all size\"},{\"name\":\"unit\",\"value\":\"kg\"},{\"name\":\"cost\",\"value\":\"20\"}]}",
                    "unit": "kg",
                    "unit_price": "0",
                    "cost": "0",
                    "total_cost": "0",
                    "margin": null,
                    "formula_mentions": "$[Gold](12) + 3",
                    "formula_data_mentions": "",
                    "gross_profit": "",
                    "description_of_formula": "",
                    "formula_scenario": "",
                    "material_data_entry": {
                        "value": "",
                        "levels": [
                            {
                                "id": 50887,
                                "name": "cong catalog",
                                "data_points": []
                            },
                            {
                                "id": 50896,
                                "name": "Shiping Cost",
                                "data_points": []
                            },
                            {
                                "id": 50897,
                                "name": "Singapore",
                                "data_points": [
                                    {
                                        "id": 78953,
                                        "name": "Singapore",
                                        "linked_description": "aaaa"
                                    }
                                ]
                            }
                        ],
                        "data_entry": {
                            "id": 324,
                            "name": "Shipping Entry00",
                            "unit": null,
                            "levels": [
                                {
                                    "id": 50887,
                                    "name": "cong catalog",
                                    "data_points": []
                                },
                                {
                                    "id": 50896,
                                    "name": "Shiping Cost",
                                    "data_points": []
                                },
                                {
                                    "id": 50897,
                                    "name": "Singapore",
                                    "data_points": [
                                        {
                                            "id": 78953,
                                            "name": "Singapore",
                                            "linked_description": "aaaa"
                                        }
                                    ]
                                }
                            ],
                            "catalog": {},
                            "category": {},
                            "dropdown": [],
                            "material": {},
                            "is_dropdown": true,
                            "content_type": 75,
                            "created_date": "2024-03-19T23:21:13.694953Z",
                            "modified_date": "2024-04-09T09:05:07.883593Z",
                            "default_column": {},
                            "material_selections": [],
                            "is_material_selection": true
                        },
                        "dropdown_value": {},
                        "material_value": {
                            "id": "50897:0",
                            "cost": "20",
                            "name": "UPS - all size",
                            "unit": "kg",
                            "levels": [
                                {
                                    "id": 50887,
                                    "name": "cong catalog",
                                    "level": null,
                                    "level_index": 0
                                },
                                {
                                    "id": 50896,
                                    "name": "Shiping Cost",
                                    "level": null,
                                    "level_index": 0
                                },
                                {
                                    "id": 50897,
                                    "name": "Singapore",
                                    "level": 1692,
                                    "level_index": 0
                                }
                            ],
                            "columns": [
                                {
                                    "name": "name",
                                    "value": "UPS - all size"
                                },
                                {
                                    "name": "unit",
                                    "value": "kg"
                                },
                                {
                                    "name": "cost",
                                    "value": "20"
                                }
                            ]
                        }
                    },
                    "formula_for_data_view": 83176,
                    "original": 83245,
                    "catalog_materials": [
                        {
                            "id": 50887,
                            "name": "cong catalog",
                            "level": null,
                            "level_index": 0
                        },
                        {
                            "id": 50896,
                            "name": "Shiping Cost",
                            "level": null,
                            "level_index": 0
                        },
                        {
                            "id": 50897,
                            "name": "Singapore",
                            "level": 1692,
                            "level_index": 0
                        }
                    ],
                    "order": 0,
                    "default_column": {
                        "name": "name",
                        "value": "UPS - all size"
                    },
                    "order_quantity": "15",
                    "selected_description": null,
                    "is_custom_po": false,
                    "user_create": 5,
                    "user_update": null,
                    "company": 1,
                    "group": null,
                    "assemble": 45637,
                    "content_type": 57,
                    "catalog_ancestor": 50887,
                    "catalog_link": [
                        {
                            "id": 50887,
                            "name": "cong catalog",
                            "level": null,
                            "level_index": 0
                        },
                        {
                            "id": 50896,
                            "name": "Shiping Cost",
                            "level": null,
                            "level_index": 0
                        },
                        {
                            "id": 50897,
                            "name": "Singapore",
                            "level": 1692,
                            "level_index": 0
                        }
                    ],
                    "material_value": {
                        "name": "UPS - all size",
                        "unit": "kg",
                        "cost": "20",
                        "id": "50897:0",
                        "levels": [
                            {
                                "id": 50887,
                                "name": "cong catalog",
                                "level": null,
                                "level_index": 0
                            },
                            {
                                "id": 50896,
                                "name": "Shiping Cost",
                                "level": null,
                                "level_index": 0
                            },
                            {
                                "id": 50897,
                                "name": "Singapore",
                                "level": 1692,
                                "level_index": 0
                            }
                        ],
                        "columns": [
                            {
                                "name": "name",
                                "value": "UPS - all size"
                            },
                            {
                                "name": "unit",
                                "value": "kg"
                            },
                            {
                                "name": "cost",
                                "value": "20"
                            }
                        ]
                    },
                    "status": true
                }
            ],
            "description": "",
            "is_show": false,
            "original": 44049,
            "is_custom_assemble": false,
            "content_type": 82
        },
        {
            "id": 45638,
            "name": "this use entries 1 and enstries 2",
            "created_date": "2024-05-31T07:25:19.322124Z",
            "modified_date": "2024-05-31T07:25:19.322139Z",
            "user_create": 5,
            "user_update": null,
            "assemble_formulas": [
                {
                    "id": 85761,
                    "self_data_entries": [
                        {
                            "id": 168343,
                            "value": "",
                            "data_entry": {
                                "id": 382,
                                "name": "new unit type",
                                "unit": {
                                    "id": 311,
                                    "name": "new unit type"
                                },
                                "dropdown": [
                                    {
                                        "name": "",
                                        "value": ""
                                    }
                                ],
                                "is_dropdown": false,
                                "is_material_selection": false,
                                "material_selections": [],
                                "created_date": "2024-04-02T08:27:04.477884Z",
                                "modified_date": "2024-04-02T08:27:04.477903Z",
                                "levels": [],
                                "material": {},
                                "default_column": {},
                                "content_type": 75,
                                "catalog": {},
                                "category": {}
                            },
                            "index": null,
                            "dropdown_value": {},
                            "material_value": {},
                            "nick_name": "new unit type",
                            "copies_from": null,
                            "group": "",
                            "material_data_entry_link": null,
                            "levels": [],
                            "is_client_view": true,
                            "po_group_index": 0,
                            "po_index": 0,
                            "custom_group_name": "Default",
                            "custom_group_index": 0,
                            "custom_index": 0,
                            "custom_po_index": 0,
                            "is_lock_estimate": false,
                            "is_lock_proposal": false,
                            "is_press_enter": false,
                            "default_value": "",
                            "default_dropdown_value": {},
                            "default_material_value": {},
                            "po_group_name": "this have 2 data entries"
                        },
                        {
                            "id": 168344,
                            "value": "",
                            "data_entry": {
                                "id": 380,
                                "name": "2.00",
                                "unit": {
                                    "id": 232,
                                    "name": "box"
                                },
                                "dropdown": [
                                    {
                                        "name": "",
                                        "value": ""
                                    }
                                ],
                                "is_dropdown": false,
                                "is_material_selection": false,
                                "material_selections": [],
                                "created_date": "2024-04-02T04:44:05.350112Z",
                                "modified_date": "2024-04-02T04:44:05.350131Z",
                                "levels": [],
                                "material": {},
                                "default_column": {},
                                "content_type": 75,
                                "catalog": {},
                                "category": {}
                            },
                            "index": null,
                            "dropdown_value": {},
                            "material_value": {},
                            "nick_name": "2.00",
                            "copies_from": null,
                            "group": "",
                            "material_data_entry_link": null,
                            "levels": [],
                            "is_client_view": true,
                            "po_group_index": 0,
                            "po_index": 0,
                            "custom_group_name": "Default",
                            "custom_group_index": 0,
                            "custom_index": 0,
                            "custom_po_index": 0,
                            "is_lock_estimate": false,
                            "is_lock_proposal": false,
                            "is_press_enter": false,
                            "default_value": "",
                            "default_dropdown_value": {},
                            "default_material_value": {},
                            "po_group_name": "this have 2 data entries"
                        },
                        {
                            "id": 168345,
                            "value": "",
                            "data_entry": {
                                "id": 322,
                                "name": "Track Loader?",
                                "unit": null,
                                "dropdown": [
                                    {
                                        "id": 1,
                                        "name": "Yes Large ",
                                        "value": "0.20"
                                    },
                                    {
                                        "id": 2,
                                        "name": "Yes Medium",
                                        "value": "0.40"
                                    },
                                    {
                                        "id": 3,
                                        "name": "Yes Small ",
                                        "value": "0.60"
                                    },
                                    {
                                        "id": 4,
                                        "name": "No",
                                        "value": "1"
                                    }
                                ],
                                "is_dropdown": true,
                                "is_material_selection": false,
                                "material_selections": [],
                                "created_date": "2024-03-19T23:13:21.482696Z",
                                "modified_date": "2024-03-19T23:13:21.482715Z",
                                "levels": [],
                                "material": {},
                                "default_column": {},
                                "content_type": 75,
                                "catalog": {},
                                "category": {}
                            },
                            "index": null,
                            "dropdown_value": {},
                            "material_value": {},
                            "nick_name": "Track Loader?",
                            "copies_from": null,
                            "group": "",
                            "material_data_entry_link": null,
                            "levels": [],
                            "is_client_view": true,
                            "po_group_index": 0,
                            "po_index": 0,
                            "custom_group_name": "Default",
                            "custom_group_index": 0,
                            "custom_index": 0,
                            "custom_po_index": 0,
                            "is_lock_estimate": false,
                            "is_lock_proposal": false,
                            "is_press_enter": false,
                            "default_value": "",
                            "default_dropdown_value": {},
                            "default_material_value": {},
                            "po_group_name": "this have 2 data entries"
                        },
                        {
                            "id": 168340,
                            "value": "",
                            "data_entry": {
                                "id": 472,
                                "name": "entries 1",
                                "unit": null,
                                "dropdown": [
                                    {
                                        "id": 1,
                                        "name": "abc",
                                        "value": "12"
                                    }
                                ],
                                "is_dropdown": true,
                                "is_material_selection": false,
                                "material_selections": [],
                                "created_date": "2024-05-08T02:25:55.792811Z",
                                "modified_date": "2024-05-08T02:25:55.792831Z",
                                "levels": [],
                                "material": {},
                                "default_column": {},
                                "content_type": 75,
                                "catalog": {},
                                "category": {}
                            },
                            "index": null,
                            "dropdown_value": {
                                "id": 1,
                                "name": "abc",
                                "value": "12"
                            },
                            "material_value": {},
                            "nick_name": "entries 1",
                            "copies_from": null,
                            "group": "",
                            "material_data_entry_link": null,
                            "levels": [],
                            "is_client_view": true,
                            "po_group_index": 0,
                            "po_index": 0,
                            "custom_group_name": "Default",
                            "custom_group_index": 0,
                            "custom_index": 0,
                            "custom_po_index": 0,
                            "is_lock_estimate": false,
                            "is_lock_proposal": false,
                            "is_press_enter": false,
                            "default_value": "",
                            "default_dropdown_value": {},
                            "default_material_value": {},
                            "po_group_name": "this have 2 data entries"
                        },
                        {
                            "id": 168341,
                            "value": "",
                            "data_entry": {
                                "id": 471,
                                "name": "entries 2",
                                "unit": null,
                                "dropdown": [
                                    {
                                        "id": 1,
                                        "name": "drop 1",
                                        "value": "2"
                                    },
                                    {
                                        "id": 2,
                                        "name": "drop 3",
                                        "value": "4"
                                    }
                                ],
                                "is_dropdown": true,
                                "is_material_selection": false,
                                "material_selections": [],
                                "created_date": "2024-05-08T02:24:54.927380Z",
                                "modified_date": "2024-05-08T02:24:54.927396Z",
                                "levels": [],
                                "material": {},
                                "default_column": {},
                                "content_type": 75,
                                "catalog": {},
                                "category": {}
                            },
                            "index": null,
                            "dropdown_value": {
                                "id": 1,
                                "name": "drop 1",
                                "value": "2"
                            },
                            "material_value": {},
                            "nick_name": "entries 2",
                            "copies_from": null,
                            "group": "",
                            "material_data_entry_link": null,
                            "levels": [],
                            "is_client_view": true,
                            "po_group_index": 0,
                            "po_index": 0,
                            "custom_group_name": "Default",
                            "custom_group_index": 0,
                            "custom_index": 0,
                            "custom_po_index": 0,
                            "is_lock_estimate": false,
                            "is_lock_proposal": false,
                            "is_press_enter": false,
                            "default_value": "",
                            "default_dropdown_value": {},
                            "default_material_value": {},
                            "po_group_name": "this have 2 data entries"
                        },
                        {
                            "id": 168342,
                            "value": "",
                            "data_entry": {
                                "id": 409,
                                "name": "Quantity",
                                "unit": {
                                    "id": 230,
                                    "name": "Ton"
                                },
                                "dropdown": [
                                    {
                                        "name": "",
                                        "value": ""
                                    }
                                ],
                                "is_dropdown": false,
                                "is_material_selection": false,
                                "material_selections": [],
                                "created_date": "2024-04-09T04:54:59.454851Z",
                                "modified_date": "2024-04-09T04:54:59.454867Z",
                                "levels": [],
                                "material": {},
                                "default_column": {},
                                "content_type": 75,
                                "catalog": {},
                                "category": {}
                            },
                            "index": null,
                            "dropdown_value": {},
                            "material_value": {},
                            "nick_name": "Quantity",
                            "copies_from": null,
                            "group": "",
                            "material_data_entry_link": null,
                            "levels": [],
                            "is_client_view": true,
                            "po_group_index": 0,
                            "po_index": 0,
                            "custom_group_name": "Default",
                            "custom_group_index": 0,
                            "custom_index": 0,
                            "custom_po_index": 0,
                            "is_lock_estimate": false,
                            "is_lock_proposal": false,
                            "is_press_enter": false,
                            "default_value": "",
                            "default_dropdown_value": {},
                            "default_material_value": {},
                            "po_group_name": "this have 2 data entries"
                        }
                    ],
                    "round_up": {
                        "type": "whole_number",
                        "whole_number": null,
                        "increments": [],
                        "last_action": "none",
                        "action_value": null
                    },
                    "created_date": "2024-05-31T07:25:19.334532Z",
                    "modified_date": "2024-05-31T07:25:19.334547Z",
                    "name": "this have 2 data entries",
                    "linked_description": [],
                    "formula": "entries 1  + entries 2",
                    "created_from": null,
                    "is_show": false,
                    "quantity": "0",
                    "markup": null,
                    "charge": "0",
                    "material": "{\"name\":\"Name 33fxx\",\"unit\":\"Gold1\",\"cost\":\"2\",\"Random thing\":\"2\",\"id\":\"50879:0\",\"levels\":[{\"id\":4626,\"name\":\"Materials\",\"level\":null,\"level_index\":0},{\"id\":4627,\"name\":\"Drainage\",\"level\":null,\"level_index\":0},{\"id\":6306,\"name\":\"Children 2\",\"level\":728,\"level_index\":0},{\"id\":50879,\"name\":\"hello 4\",\"level\":927,\"level_index\":1}],\"columns\":[{\"name\":\"name\",\"value\":\"Name 33fxx\"},{\"name\":\"unit\",\"value\":\"Gold1\"},{\"name\":\"cost\",\"value\":\"2\"},{\"name\":\"Random thing\",\"value\":\"2\"}]}",
                    "unit": "Gold1",
                    "unit_price": "2",
                    "cost": "2",
                    "total_cost": "0",
                    "margin": null,
                    "formula_mentions": "$[entries 1](472)  + $[entries 2](472)",
                    "formula_data_mentions": "",
                    "gross_profit": "",
                    "description_of_formula": "",
                    "formula_scenario": "",
                    "material_data_entry": {},
                    "formula_for_data_view": 83163,
                    "original": 83232,
                    "catalog_materials": [
                        {
                            "id": 4626,
                            "name": "Materials",
                            "level": null,
                            "level_index": 0
                        },
                        {
                            "id": 4627,
                            "name": "Drainage",
                            "level": null,
                            "level_index": 0
                        },
                        {
                            "id": 6306,
                            "name": "Children 2",
                            "level": 728,
                            "level_index": 0
                        },
                        {
                            "id": 50879,
                            "name": "hello 4",
                            "level": 927,
                            "level_index": 1
                        }
                    ],
                    "order": 0,
                    "default_column": {
                        "name": "cost",
                        "value": "2"
                    },
                    "order_quantity": "0",
                    "selected_description": null,
                    "is_custom_po": false,
                    "user_create": 5,
                    "user_update": null,
                    "company": 1,
                    "group": null,
                    "assemble": 45638,
                    "content_type": 57,
                    "catalog_ancestor": 4626,
                    "catalog_link": [
                        {
                            "id": 4626,
                            "name": "Materials",
                            "level": null,
                            "level_index": 0
                        },
                        {
                            "id": 4627,
                            "name": "Drainage",
                            "level": null,
                            "level_index": 0
                        },
                        {
                            "id": 6306,
                            "name": "Children 2",
                            "level": 728,
                            "level_index": 0
                        },
                        {
                            "id": 50879,
                            "name": "hello 4",
                            "level": 927,
                            "level_index": 1
                        }
                    ],
                    "material_value": {
                        "name": "Name 33fxx",
                        "unit": "Gold1",
                        "cost": "2",
                        "Random thing": "2",
                        "id": "50879:0",
                        "levels": [
                            {
                                "id": 4626,
                                "name": "Materials",
                                "level": null,
                                "level_index": 0
                            },
                            {
                                "id": 4627,
                                "name": "Drainage",
                                "level": null,
                                "level_index": 0
                            },
                            {
                                "id": 6306,
                                "name": "Children 2",
                                "level": 728,
                                "level_index": 0
                            },
                            {
                                "id": 50879,
                                "name": "hello 4",
                                "level": 927,
                                "level_index": 1
                            }
                        ],
                        "columns": [
                            {
                                "name": "name",
                                "value": "Name 33fxx"
                            },
                            {
                                "name": "unit",
                                "value": "Gold1"
                            },
                            {
                                "name": "cost",
                                "value": "2"
                            },
                            {
                                "name": "Random thing",
                                "value": "2"
                            }
                        ]
                    },
                    "status": true
                }
            ],
            "description": "",
            "is_show": false,
            "original": 44038,
            "is_custom_assemble": false,
            "content_type": 82
        },
        {
            "id": 45639,
            "name": "this also use entries 1 and 2",
            "created_date": "2024-05-31T07:25:19.360782Z",
            "modified_date": "2024-05-31T07:25:19.360798Z",
            "user_create": 5,
            "user_update": null,
            "assemble_formulas": [
                {
                    "id": 85762,
                    "self_data_entries": [
                        {
                            "id": 168346,
                            "value": "",
                            "data_entry": {
                                "id": 472,
                                "name": "entries 1",
                                "unit": null,
                                "dropdown": [
                                    {
                                        "id": 1,
                                        "name": "abc",
                                        "value": "12"
                                    }
                                ],
                                "is_dropdown": true,
                                "is_material_selection": false,
                                "material_selections": [],
                                "created_date": "2024-05-08T02:25:55.792811Z",
                                "modified_date": "2024-05-08T02:25:55.792831Z",
                                "levels": [],
                                "material": {},
                                "default_column": {},
                                "content_type": 75,
                                "catalog": {},
                                "category": {}
                            },
                            "index": null,
                            "dropdown_value": {},
                            "material_value": {},
                            "nick_name": "entries 1",
                            "copies_from": null,
                            "group": "",
                            "material_data_entry_link": null,
                            "levels": [],
                            "is_client_view": true,
                            "po_group_index": 0,
                            "po_index": 0,
                            "custom_group_name": "Default",
                            "custom_group_index": 0,
                            "custom_index": 0,
                            "custom_po_index": 0,
                            "is_lock_estimate": false,
                            "is_lock_proposal": false,
                            "is_press_enter": false,
                            "default_value": "",
                            "default_dropdown_value": {},
                            "default_material_value": {},
                            "po_group_name": "this use 2 data entries with 1"
                        },
                        {
                            "id": 168347,
                            "value": "",
                            "data_entry": {
                                "id": 250,
                                "name": "lolipop",
                                "unit": {
                                    "id": 54,
                                    "name": "test 03"
                                },
                                "dropdown": [
                                    {
                                        "name": "",
                                        "value": ""
                                    }
                                ],
                                "is_dropdown": false,
                                "is_material_selection": false,
                                "material_selections": [],
                                "created_date": "2024-01-29T02:43:00.174839Z",
                                "modified_date": "2024-01-29T02:43:00.174858Z",
                                "levels": [],
                                "material": {},
                                "default_column": {},
                                "content_type": 75,
                                "catalog": {},
                                "category": {}
                            },
                            "index": null,
                            "dropdown_value": {},
                            "material_value": {},
                            "nick_name": "lolipop",
                            "copies_from": null,
                            "group": "",
                            "material_data_entry_link": null,
                            "levels": [],
                            "is_client_view": true,
                            "po_group_index": 0,
                            "po_index": 0,
                            "custom_group_name": "Default",
                            "custom_group_index": 0,
                            "custom_index": 0,
                            "custom_po_index": 0,
                            "is_lock_estimate": false,
                            "is_lock_proposal": false,
                            "is_press_enter": false,
                            "default_value": "",
                            "default_dropdown_value": {},
                            "default_material_value": {},
                            "po_group_name": "this use 2 data entries with 1"
                        }
                    ],
                    "round_up": {
                        "type": "whole_number",
                        "whole_number": null,
                        "increments": [],
                        "last_action": "none",
                        "action_value": null
                    },
                    "created_date": "2024-05-31T07:25:19.370953Z",
                    "modified_date": "2024-05-31T07:25:19.370968Z",
                    "name": "this use 2 data entries with 1",
                    "linked_description": [],
                    "formula": "lolipop + entries 1",
                    "created_from": null,
                    "is_show": false,
                    "quantity": null,
                    "markup": null,
                    "charge": null,
                    "material": "{}",
                    "unit": "",
                    "unit_price": "0",
                    "cost": "0",
                    "total_cost": null,
                    "margin": null,
                    "formula_mentions": "$[lolipop](250) + $[entries 1](472)",
                    "formula_data_mentions": "",
                    "gross_profit": "",
                    "description_of_formula": "",
                    "formula_scenario": "",
                    "material_data_entry": {},
                    "formula_for_data_view": 82265,
                    "original": 82265,
                    "catalog_materials": [
                        null
                    ],
                    "order": 0,
                    "default_column": {},
                    "order_quantity": null,
                    "selected_description": null,
                    "is_custom_po": false,
                    "user_create": 5,
                    "user_update": null,
                    "company": 1,
                    "group": null,
                    "assemble": 45639,
                    "content_type": 57,
                    "catalog_ancestor": null,
                    "catalog_link": [],
                    "material_value": {},
                    "status": true
                }
            ],
            "description": "",
            "is_show": false,
            "original": 43411,
            "is_custom_assemble": false,
            "content_type": 82
        },
        {
            "id": 45640,
            "name": "L'sn 222",
            "created_date": "2024-05-31T07:25:19.412511Z",
            "modified_date": "2024-05-31T07:25:19.412527Z",
            "user_create": 5,
            "user_update": null,
            "assemble_formulas": [
                {
                    "id": 85763,
                    "self_data_entries": [
                        {
                            "id": 168348,
                            "value": "0.00",
                            "data_entry": {
                                "id": 323,
                                "name": "Quantity with relation00",
                                "unit": null,
                                "dropdown": [
                                    {
                                        "id": 1,
                                        "name": "custom",
                                        "value": "10"
                                    }
                                ],
                                "is_dropdown": true,
                                "is_material_selection": false,
                                "material_selections": [],
                                "created_date": "2024-03-19T23:19:59.951365Z",
                                "modified_date": "2024-04-09T09:04:06.050493Z",
                                "levels": [],
                                "material": {},
                                "default_column": {},
                                "content_type": 75,
                                "catalog": {},
                                "category": {}
                            },
                            "index": null,
                            "dropdown_value": {},
                            "material_value": {},
                            "nick_name": "Quantity with relation00",
                            "copies_from": null,
                            "group": "",
                            "material_data_entry_link": null,
                            "levels": [],
                            "is_client_view": true,
                            "po_group_index": 0,
                            "po_index": 0,
                            "custom_group_name": "Default",
                            "custom_group_index": 0,
                            "custom_index": 0,
                            "custom_po_index": 0,
                            "is_lock_estimate": false,
                            "is_lock_proposal": false,
                            "is_press_enter": false,
                            "default_value": "",
                            "default_dropdown_value": {},
                            "default_material_value": {},
                            "po_group_name": "update empty data entry 2 (2)"
                        },
                        {
                            "id": 168349,
                            "value": "",
                            "data_entry": {
                                "id": 472,
                                "name": "entries 1",
                                "unit": null,
                                "dropdown": [
                                    {
                                        "id": 1,
                                        "name": "abc",
                                        "value": "12"
                                    }
                                ],
                                "is_dropdown": true,
                                "is_material_selection": false,
                                "material_selections": [],
                                "created_date": "2024-05-08T02:25:55.792811Z",
                                "modified_date": "2024-05-08T02:25:55.792831Z",
                                "levels": [],
                                "material": {},
                                "default_column": {},
                                "content_type": 75,
                                "catalog": {},
                                "category": {}
                            },
                            "index": null,
                            "dropdown_value": {
                                "id": 1,
                                "name": "abc",
                                "value": "12"
                            },
                            "material_value": {},
                            "nick_name": "entries 1",
                            "copies_from": null,
                            "group": "",
                            "material_data_entry_link": null,
                            "levels": [],
                            "is_client_view": true,
                            "po_group_index": 0,
                            "po_index": 0,
                            "custom_group_name": "Default",
                            "custom_group_index": 0,
                            "custom_index": 0,
                            "custom_po_index": 0,
                            "is_lock_estimate": false,
                            "is_lock_proposal": false,
                            "is_press_enter": false,
                            "default_value": "",
                            "default_dropdown_value": {},
                            "default_material_value": {},
                            "po_group_name": "update empty data entry 2 (2)"
                        },
                        {
                            "id": 168350,
                            "value": "",
                            "data_entry": {
                                "id": 471,
                                "name": "entries 2",
                                "unit": null,
                                "dropdown": [
                                    {
                                        "id": 1,
                                        "name": "drop 1",
                                        "value": "2"
                                    },
                                    {
                                        "id": 2,
                                        "name": "drop 3",
                                        "value": "4"
                                    }
                                ],
                                "is_dropdown": true,
                                "is_material_selection": false,
                                "material_selections": [],
                                "created_date": "2024-05-08T02:24:54.927380Z",
                                "modified_date": "2024-05-08T02:24:54.927396Z",
                                "levels": [],
                                "material": {},
                                "default_column": {},
                                "content_type": 75,
                                "catalog": {},
                                "category": {}
                            },
                            "index": null,
                            "dropdown_value": {
                                "id": 1,
                                "name": "drop 1",
                                "value": "2"
                            },
                            "material_value": {},
                            "nick_name": "entries 2",
                            "copies_from": null,
                            "group": "",
                            "material_data_entry_link": null,
                            "levels": [],
                            "is_client_view": true,
                            "po_group_index": 0,
                            "po_index": 0,
                            "custom_group_name": "Default",
                            "custom_group_index": 0,
                            "custom_index": 0,
                            "custom_po_index": 0,
                            "is_lock_estimate": false,
                            "is_lock_proposal": false,
                            "is_press_enter": false,
                            "default_value": "",
                            "default_dropdown_value": {},
                            "default_material_value": {},
                            "po_group_name": "update empty data entry 2 (2)"
                        }
                    ],
                    "round_up": {
                        "type": "increment",
                        "whole_number": null,
                        "increments": [
                            {
                                "value": "5"
                            },
                            {
                                "value": 0
                            }
                        ],
                        "last_action": "none",
                        "action_value": null
                    },
                    "created_date": "2024-05-31T07:25:19.424154Z",
                    "modified_date": "2024-05-31T07:25:19.424178Z",
                    "name": "update empty data entry 2 (2)",
                    "linked_description": [],
                    "formula": "1 + 92",
                    "created_from": null,
                    "is_show": false,
                    "quantity": "93",
                    "markup": "25",
                    "charge": "11625",
                    "material": "{\"id\":\"771:0\",\"bud\":\"2 + @[material 1 -cost](771material 1 cost) \",\"cost\":\"100\",\"name\":\"material 1 \",\"unit\":\"Gold2\",\"Cost 2\":\"1\",\"levels\":[{\"id\":192,\"name\":\"Nana Coffee's\",\"level\":null,\"level_index\":0},{\"id\":193,\"name\":\"Drinks\",\"level\":null,\"level_index\":0},{\"id\":195,\"name\":\"Carrot Juice\",\"level\":75,\"level_index\":0},{\"id\":771,\"name\":\"abc\",\"level\":76,\"level_index\":1}],\"columns\":[{\"name\":\"name\",\"value\":\"material 1 \"},{\"name\":\"unit\",\"value\":\"Gold2\"},{\"name\":\"cost\",\"value\":\"100\"},{\"name\":\"Cost 2\",\"value\":\"1\"},{\"name\":\"bud\",\"value\":\"2 + @[material 1 -cost](771material 1 cost) \"}]}",
                    "unit": "Gold2",
                    "unit_price": "125",
                    "cost": "100",
                    "total_cost": "9300",
                    "margin": "2325",
                    "formula_mentions": "1 + 92",
                    "formula_data_mentions": "",
                    "gross_profit": "",
                    "description_of_formula": "",
                    "formula_scenario": "",
                    "material_data_entry": {
                        "value": "",
                        "levels": [
                            {
                                "id": 192,
                                "name": "Nana Coffee's",
                                "data_points": []
                            },
                            {
                                "id": 193,
                                "name": "Drinks",
                                "data_points": []
                            },
                            {
                                "id": 195,
                                "name": "Carrot Juice",
                                "data_points": [
                                    {
                                        "id": 5442,
                                        "name": "Carrot Juice",
                                        "linked_description": ""
                                    },
                                    {
                                        "id": 417,
                                        "name": "Carrot Juice",
                                        "linked_description": ""
                                    }
                                ]
                            },
                            {
                                "id": 771,
                                "name": "abc",
                                "data_points": [
                                    {
                                        "id": 5444,
                                        "name": "abc",
                                        "linked_description": ""
                                    }
                                ]
                            }
                        ],
                        "data_entry": {
                            "id": 274,
                            "name": "L material select",
                            "unit": null,
                            "levels": [
                                {
                                    "id": 192,
                                    "name": "Nana Coffee's",
                                    "data_points": []
                                },
                                {
                                    "id": 193,
                                    "name": "Drinks",
                                    "data_points": []
                                },
                                {
                                    "id": 195,
                                    "name": "Carrot Juice",
                                    "data_points": [
                                        {
                                            "id": 5442,
                                            "name": "Carrot Juice",
                                            "linked_description": ""
                                        },
                                        {
                                            "id": 417,
                                            "name": "Carrot Juice",
                                            "linked_description": ""
                                        }
                                    ]
                                },
                                {
                                    "id": 771,
                                    "name": "abc",
                                    "data_points": [
                                        {
                                            "id": 5444,
                                            "name": "abc",
                                            "linked_description": ""
                                        }
                                    ]
                                }
                            ],
                            "catalog": {},
                            "category": {},
                            "dropdown": [],
                            "material": {
                                "id": "771:0",
                                "bud": "2 + @[material 1 -cost](771material 1 cost) ",
                                "cost": "100",
                                "name": "material 1 ",
                                "unit": "Gold2",
                                "Cost 2": "1",
                                "levels": [
                                    {
                                        "id": 192,
                                        "name": "Nana Coffee's",
                                        "level": null,
                                        "level_index": 0
                                    },
                                    {
                                        "id": 193,
                                        "name": "Drinks",
                                        "level": null,
                                        "level_index": 0
                                    },
                                    {
                                        "id": 195,
                                        "name": "Carrot Juice",
                                        "level": 75,
                                        "level_index": 0
                                    },
                                    {
                                        "id": 771,
                                        "name": "abc",
                                        "level": 76,
                                        "level_index": 1
                                    }
                                ],
                                "columns": [
                                    {
                                        "name": "name",
                                        "value": "material 1 "
                                    },
                                    {
                                        "name": "unit",
                                        "value": "Gold2"
                                    },
                                    {
                                        "name": "cost",
                                        "value": "100"
                                    },
                                    {
                                        "name": "Cost 2",
                                        "value": "1"
                                    },
                                    {
                                        "name": "bud",
                                        "value": "2 + @[material 1 -cost](771material 1 cost) "
                                    }
                                ]
                            },
                            "is_dropdown": true,
                            "content_type": 75,
                            "created_date": "2024-02-23T03:44:55.747881Z",
                            "modified_date": "2024-02-23T03:44:55.747899Z",
                            "default_column": {
                                "name": "cost",
                                "value": "100"
                            },
                            "material_selections": [],
                            "is_material_selection": true
                        },
                        "dropdown_value": {},
                        "material_value": {
                            "id": "771:0",
                            "bud": "2 + @[material 1 -cost](771material 1 cost) ",
                            "cost": "100",
                            "name": "material 1 ",
                            "unit": "Gold2",
                            "Cost 2": "1",
                            "levels": [
                                {
                                    "id": 192,
                                    "name": "Nana Coffee's",
                                    "level": null,
                                    "level_index": 0
                                },
                                {
                                    "id": 193,
                                    "name": "Drinks",
                                    "level": null,
                                    "level_index": 0
                                },
                                {
                                    "id": 195,
                                    "name": "Carrot Juice",
                                    "level": 75,
                                    "level_index": 0
                                },
                                {
                                    "id": 771,
                                    "name": "abc",
                                    "level": 76,
                                    "level_index": 1
                                }
                            ],
                            "columns": [
                                {
                                    "name": "name",
                                    "value": "material 1 "
                                },
                                {
                                    "name": "unit",
                                    "value": "Gold2"
                                },
                                {
                                    "name": "cost",
                                    "value": "100"
                                },
                                {
                                    "name": "Cost 2",
                                    "value": "1"
                                },
                                {
                                    "name": "bud",
                                    "value": "2 + @[material 1 -cost](771material 1 cost) "
                                }
                            ]
                        }
                    },
                    "formula_for_data_view": 13443,
                    "original": 82178,
                    "catalog_materials": [
                        {
                            "id": 192,
                            "name": "Nana Coffee's",
                            "level": null,
                            "level_index": 0
                        },
                        {
                            "id": 193,
                            "name": "Drinks",
                            "level": null,
                            "level_index": 0
                        },
                        {
                            "id": 195,
                            "name": "Carrot Juice",
                            "level": 75,
                            "level_index": 0
                        },
                        {
                            "id": 771,
                            "name": "abc",
                            "level": 76,
                            "level_index": 1
                        }
                    ],
                    "order": 0,
                    "default_column": {
                        "name": "cost",
                        "value": "100"
                    },
                    "order_quantity": "93",
                    "selected_description": -1,
                    "is_custom_po": false,
                    "user_create": 5,
                    "user_update": null,
                    "company": 1,
                    "group": null,
                    "assemble": 45640,
                    "content_type": 57,
                    "catalog_ancestor": 192,
                    "catalog_link": [
                        {
                            "id": 192,
                            "name": "Nana Coffee's",
                            "level": null,
                            "level_index": 0
                        },
                        {
                            "id": 193,
                            "name": "Drinks",
                            "level": null,
                            "level_index": 0
                        },
                        {
                            "id": 195,
                            "name": "Carrot Juice",
                            "level": 75,
                            "level_index": 0
                        },
                        {
                            "id": 771,
                            "name": "abc",
                            "level": 76,
                            "level_index": 1
                        }
                    ],
                    "material_value": {
                        "id": "771:0",
                        "bud": "2 + @[material 1 -cost](771material 1 cost) ",
                        "cost": "100",
                        "name": "material 1 ",
                        "unit": "Gold2",
                        "Cost 2": "1",
                        "levels": [
                            {
                                "id": 192,
                                "name": "Nana Coffee's",
                                "level": null,
                                "level_index": 0
                            },
                            {
                                "id": 193,
                                "name": "Drinks",
                                "level": null,
                                "level_index": 0
                            },
                            {
                                "id": 195,
                                "name": "Carrot Juice",
                                "level": 75,
                                "level_index": 0
                            },
                            {
                                "id": 771,
                                "name": "abc",
                                "level": 76,
                                "level_index": 1
                            }
                        ],
                        "columns": [
                            {
                                "name": "name",
                                "value": "material 1 "
                            },
                            {
                                "name": "unit",
                                "value": "Gold2"
                            },
                            {
                                "name": "cost",
                                "value": "100"
                            },
                            {
                                "name": "Cost 2",
                                "value": "1"
                            },
                            {
                                "name": "bud",
                                "value": "2 + @[material 1 -cost](771material 1 cost) "
                            }
                        ]
                    },
                    "status": true
                },
                {
                    "id": 85764,
                    "self_data_entries": [
                        {
                            "id": 168351,
                            "value": "0.00",
                            "data_entry": {
                                "id": 323,
                                "name": "Quantity with relation00",
                                "unit": null,
                                "dropdown": [
                                    {
                                        "id": 1,
                                        "name": "custom",
                                        "value": "10"
                                    }
                                ],
                                "is_dropdown": true,
                                "is_material_selection": false,
                                "material_selections": [],
                                "created_date": "2024-03-19T23:19:59.951365Z",
                                "modified_date": "2024-04-09T09:04:06.050493Z",
                                "levels": [],
                                "material": {},
                                "default_column": {},
                                "content_type": 75,
                                "catalog": {},
                                "category": {}
                            },
                            "index": null,
                            "dropdown_value": {},
                            "material_value": {},
                            "nick_name": "Quantity with relation00",
                            "copies_from": null,
                            "group": "",
                            "material_data_entry_link": null,
                            "levels": [],
                            "is_client_view": true,
                            "po_group_index": 0,
                            "po_index": 0,
                            "custom_group_name": "Default",
                            "custom_group_index": 0,
                            "custom_index": 0,
                            "custom_po_index": 0,
                            "is_lock_estimate": false,
                            "is_lock_proposal": false,
                            "is_press_enter": false,
                            "default_value": "",
                            "default_dropdown_value": {},
                            "default_material_value": {},
                            "po_group_name": "update empty data entry 2 (2)"
                        },
                        {
                            "id": 168352,
                            "value": "",
                            "data_entry": {
                                "id": 472,
                                "name": "entries 1",
                                "unit": null,
                                "dropdown": [
                                    {
                                        "id": 1,
                                        "name": "abc",
                                        "value": "12"
                                    }
                                ],
                                "is_dropdown": true,
                                "is_material_selection": false,
                                "material_selections": [],
                                "created_date": "2024-05-08T02:25:55.792811Z",
                                "modified_date": "2024-05-08T02:25:55.792831Z",
                                "levels": [],
                                "material": {},
                                "default_column": {},
                                "content_type": 75,
                                "catalog": {},
                                "category": {}
                            },
                            "index": null,
                            "dropdown_value": {
                                "id": 1,
                                "name": "abc",
                                "value": "12"
                            },
                            "material_value": {},
                            "nick_name": "entries 1",
                            "copies_from": null,
                            "group": "",
                            "material_data_entry_link": null,
                            "levels": [],
                            "is_client_view": true,
                            "po_group_index": 0,
                            "po_index": 0,
                            "custom_group_name": "Default",
                            "custom_group_index": 0,
                            "custom_index": 0,
                            "custom_po_index": 0,
                            "is_lock_estimate": false,
                            "is_lock_proposal": false,
                            "is_press_enter": false,
                            "default_value": "",
                            "default_dropdown_value": {},
                            "default_material_value": {},
                            "po_group_name": "update empty data entry 2 (2)"
                        },
                        {
                            "id": 168353,
                            "value": "",
                            "data_entry": {
                                "id": 471,
                                "name": "entries 2",
                                "unit": null,
                                "dropdown": [
                                    {
                                        "id": 1,
                                        "name": "drop 1",
                                        "value": "2"
                                    },
                                    {
                                        "id": 2,
                                        "name": "drop 3",
                                        "value": "4"
                                    }
                                ],
                                "is_dropdown": true,
                                "is_material_selection": false,
                                "material_selections": [],
                                "created_date": "2024-05-08T02:24:54.927380Z",
                                "modified_date": "2024-05-08T02:24:54.927396Z",
                                "levels": [],
                                "material": {},
                                "default_column": {},
                                "content_type": 75,
                                "catalog": {},
                                "category": {}
                            },
                            "index": null,
                            "dropdown_value": {
                                "id": 1,
                                "name": "drop 1",
                                "value": "2"
                            },
                            "material_value": {},
                            "nick_name": "entries 2",
                            "copies_from": null,
                            "group": "",
                            "material_data_entry_link": null,
                            "levels": [],
                            "is_client_view": true,
                            "po_group_index": 0,
                            "po_index": 0,
                            "custom_group_name": "Default",
                            "custom_group_index": 0,
                            "custom_index": 0,
                            "custom_po_index": 0,
                            "is_lock_estimate": false,
                            "is_lock_proposal": false,
                            "is_press_enter": false,
                            "default_value": "",
                            "default_dropdown_value": {},
                            "default_material_value": {},
                            "po_group_name": "update empty data entry 2 (2)"
                        }
                    ],
                    "round_up": {
                        "type": "increment",
                        "whole_number": null,
                        "increments": [
                            {
                                "value": "5"
                            },
                            {
                                "value": 0
                            }
                        ],
                        "last_action": "none",
                        "action_value": null
                    },
                    "created_date": "2024-05-31T07:25:19.444527Z",
                    "modified_date": "2024-05-31T07:25:19.444543Z",
                    "name": "update empty data entry 2 (2)",
                    "linked_description": [],
                    "formula": "1 + 92",
                    "created_from": null,
                    "is_show": false,
                    "quantity": "93",
                    "markup": "25",
                    "charge": "11625",
                    "material": "{\"id\":\"771:0\",\"bud\":\"2 + @[material 1 -cost](771material 1 cost) \",\"cost\":\"100\",\"name\":\"material 1 \",\"unit\":\"Gold2\",\"Cost 2\":\"1\",\"levels\":[{\"id\":192,\"name\":\"Nana Coffee's\",\"level\":null,\"level_index\":0},{\"id\":193,\"name\":\"Drinks\",\"level\":null,\"level_index\":0},{\"id\":195,\"name\":\"Carrot Juice\",\"level\":75,\"level_index\":0},{\"id\":771,\"name\":\"abc\",\"level\":76,\"level_index\":1}],\"columns\":[{\"name\":\"name\",\"value\":\"material 1 \"},{\"name\":\"unit\",\"value\":\"Gold2\"},{\"name\":\"cost\",\"value\":\"100\"},{\"name\":\"Cost 2\",\"value\":\"1\"},{\"name\":\"bud\",\"value\":\"2 + @[material 1 -cost](771material 1 cost) \"}]}",
                    "unit": "Gold2",
                    "unit_price": "125",
                    "cost": "100",
                    "total_cost": "9300",
                    "margin": "2325",
                    "formula_mentions": "1 + 92",
                    "formula_data_mentions": "",
                    "gross_profit": "",
                    "description_of_formula": "",
                    "formula_scenario": "",
                    "material_data_entry": {
                        "value": "",
                        "levels": [
                            {
                                "id": 192,
                                "name": "Nana Coffee's",
                                "data_points": []
                            },
                            {
                                "id": 193,
                                "name": "Drinks",
                                "data_points": []
                            },
                            {
                                "id": 195,
                                "name": "Carrot Juice",
                                "data_points": [
                                    {
                                        "id": 5442,
                                        "name": "Carrot Juice",
                                        "linked_description": ""
                                    },
                                    {
                                        "id": 417,
                                        "name": "Carrot Juice",
                                        "linked_description": ""
                                    }
                                ]
                            },
                            {
                                "id": 771,
                                "name": "abc",
                                "data_points": [
                                    {
                                        "id": 5444,
                                        "name": "abc",
                                        "linked_description": ""
                                    }
                                ]
                            }
                        ],
                        "data_entry": {
                            "id": 274,
                            "name": "L material select",
                            "unit": null,
                            "levels": [
                                {
                                    "id": 192,
                                    "name": "Nana Coffee's",
                                    "data_points": []
                                },
                                {
                                    "id": 193,
                                    "name": "Drinks",
                                    "data_points": []
                                },
                                {
                                    "id": 195,
                                    "name": "Carrot Juice",
                                    "data_points": [
                                        {
                                            "id": 5442,
                                            "name": "Carrot Juice",
                                            "linked_description": ""
                                        },
                                        {
                                            "id": 417,
                                            "name": "Carrot Juice",
                                            "linked_description": ""
                                        }
                                    ]
                                },
                                {
                                    "id": 771,
                                    "name": "abc",
                                    "data_points": [
                                        {
                                            "id": 5444,
                                            "name": "abc",
                                            "linked_description": ""
                                        }
                                    ]
                                }
                            ],
                            "catalog": {},
                            "category": {},
                            "dropdown": [],
                            "material": {
                                "id": "771:0",
                                "bud": "2 + @[material 1 -cost](771material 1 cost) ",
                                "cost": "100",
                                "name": "material 1 ",
                                "unit": "Gold2",
                                "Cost 2": "1",
                                "levels": [
                                    {
                                        "id": 192,
                                        "name": "Nana Coffee's",
                                        "level": null,
                                        "level_index": 0
                                    },
                                    {
                                        "id": 193,
                                        "name": "Drinks",
                                        "level": null,
                                        "level_index": 0
                                    },
                                    {
                                        "id": 195,
                                        "name": "Carrot Juice",
                                        "level": 75,
                                        "level_index": 0
                                    },
                                    {
                                        "id": 771,
                                        "name": "abc",
                                        "level": 76,
                                        "level_index": 1
                                    }
                                ],
                                "columns": [
                                    {
                                        "name": "name",
                                        "value": "material 1 "
                                    },
                                    {
                                        "name": "unit",
                                        "value": "Gold2"
                                    },
                                    {
                                        "name": "cost",
                                        "value": "100"
                                    },
                                    {
                                        "name": "Cost 2",
                                        "value": "1"
                                    },
                                    {
                                        "name": "bud",
                                        "value": "2 + @[material 1 -cost](771material 1 cost) "
                                    }
                                ]
                            },
                            "is_dropdown": true,
                            "content_type": 75,
                            "created_date": "2024-02-23T03:44:55.747881Z",
                            "modified_date": "2024-02-23T03:44:55.747899Z",
                            "default_column": {
                                "name": "cost",
                                "value": "100"
                            },
                            "material_selections": [],
                            "is_material_selection": true
                        },
                        "dropdown_value": {},
                        "material_value": {
                            "id": "771:0",
                            "bud": "2 + @[material 1 -cost](771material 1 cost) ",
                            "cost": "100",
                            "name": "material 1 ",
                            "unit": "Gold2",
                            "Cost 2": "1",
                            "levels": [
                                {
                                    "id": 192,
                                    "name": "Nana Coffee's",
                                    "level": null,
                                    "level_index": 0
                                },
                                {
                                    "id": 193,
                                    "name": "Drinks",
                                    "level": null,
                                    "level_index": 0
                                },
                                {
                                    "id": 195,
                                    "name": "Carrot Juice",
                                    "level": 75,
                                    "level_index": 0
                                },
                                {
                                    "id": 771,
                                    "name": "abc",
                                    "level": 76,
                                    "level_index": 1
                                }
                            ],
                            "columns": [
                                {
                                    "name": "name",
                                    "value": "material 1 "
                                },
                                {
                                    "name": "unit",
                                    "value": "Gold2"
                                },
                                {
                                    "name": "cost",
                                    "value": "100"
                                },
                                {
                                    "name": "Cost 2",
                                    "value": "1"
                                },
                                {
                                    "name": "bud",
                                    "value": "2 + @[material 1 -cost](771material 1 cost) "
                                }
                            ]
                        }
                    },
                    "formula_for_data_view": 13443,
                    "original": 82178,
                    "catalog_materials": [
                        {
                            "id": 192,
                            "name": "Nana Coffee's",
                            "level": null,
                            "level_index": 0
                        },
                        {
                            "id": 193,
                            "name": "Drinks",
                            "level": null,
                            "level_index": 0
                        },
                        {
                            "id": 195,
                            "name": "Carrot Juice",
                            "level": 75,
                            "level_index": 0
                        },
                        {
                            "id": 771,
                            "name": "abc",
                            "level": 76,
                            "level_index": 1
                        }
                    ],
                    "order": 0,
                    "default_column": {
                        "name": "cost",
                        "value": "100"
                    },
                    "order_quantity": "93",
                    "selected_description": -1,
                    "is_custom_po": false,
                    "user_create": 5,
                    "user_update": null,
                    "company": 1,
                    "group": null,
                    "assemble": 45640,
                    "content_type": 57,
                    "catalog_ancestor": 192,
                    "catalog_link": [
                        {
                            "id": 192,
                            "name": "Nana Coffee's",
                            "level": null,
                            "level_index": 0
                        },
                        {
                            "id": 193,
                            "name": "Drinks",
                            "level": null,
                            "level_index": 0
                        },
                        {
                            "id": 195,
                            "name": "Carrot Juice",
                            "level": 75,
                            "level_index": 0
                        },
                        {
                            "id": 771,
                            "name": "abc",
                            "level": 76,
                            "level_index": 1
                        }
                    ],
                    "material_value": {
                        "id": "771:0",
                        "bud": "2 + @[material 1 -cost](771material 1 cost) ",
                        "cost": "100",
                        "name": "material 1 ",
                        "unit": "Gold2",
                        "Cost 2": "1",
                        "levels": [
                            {
                                "id": 192,
                                "name": "Nana Coffee's",
                                "level": null,
                                "level_index": 0
                            },
                            {
                                "id": 193,
                                "name": "Drinks",
                                "level": null,
                                "level_index": 0
                            },
                            {
                                "id": 195,
                                "name": "Carrot Juice",
                                "level": 75,
                                "level_index": 0
                            },
                            {
                                "id": 771,
                                "name": "abc",
                                "level": 76,
                                "level_index": 1
                            }
                        ],
                        "columns": [
                            {
                                "name": "name",
                                "value": "material 1 "
                            },
                            {
                                "name": "unit",
                                "value": "Gold2"
                            },
                            {
                                "name": "cost",
                                "value": "100"
                            },
                            {
                                "name": "Cost 2",
                                "value": "1"
                            },
                            {
                                "name": "bud",
                                "value": "2 + @[material 1 -cost](771material 1 cost) "
                            }
                        ]
                    },
                    "status": true
                }
            ],
            "description": "",
            "is_show": false,
            "original": 43382,
            "is_custom_assemble": false,
            "content_type": 82
        },
        {
            "id": 45641,
            "name": "Assembly with empty formula",
            "created_date": "2024-05-31T07:25:19.455649Z",
            "modified_date": "2024-05-31T07:25:19.455662Z",
            "user_create": 5,
            "user_update": null,
            "assemble_formulas": [
                {
                    "id": 85765,
                    "self_data_entries": [],
                    "round_up": {
                        "type": "whole_number",
                        "whole_number": null,
                        "increments": [],
                        "last_action": "none",
                        "action_value": null
                    },
                    "created_date": "2024-05-31T07:25:19.460126Z",
                    "modified_date": "2024-05-31T07:25:19.460140Z",
                    "name": "empty formula",
                    "linked_description": [],
                    "formula": "",
                    "created_from": null,
                    "is_show": false,
                    "quantity": "0",
                    "markup": null,
                    "charge": "0",
                    "material": "{}",
                    "unit": "",
                    "unit_price": "0",
                    "cost": "0",
                    "total_cost": "0",
                    "margin": null,
                    "formula_mentions": "",
                    "formula_data_mentions": "",
                    "gross_profit": "",
                    "description_of_formula": "",
                    "formula_scenario": "",
                    "material_data_entry": {},
                    "formula_for_data_view": 72334,
                    "original": 72334,
                    "catalog_materials": [
                        null
                    ],
                    "order": 0,
                    "default_column": {},
                    "order_quantity": "0",
                    "selected_description": null,
                    "is_custom_po": false,
                    "user_create": 5,
                    "user_update": null,
                    "company": 1,
                    "group": null,
                    "assemble": 45641,
                    "content_type": 57,
                    "catalog_ancestor": null,
                    "catalog_link": [],
                    "material_value": {},
                    "status": false
                }
            ],
            "description": "",
            "is_show": false,
            "original": 38102,
            "is_custom_assemble": false,
            "content_type": 82
        },
        {
            "id": 45642,
            "name": "123 2 co description 1",
            "created_date": "2024-05-31T07:25:19.476830Z",
            "modified_date": "2024-05-31T07:25:19.476846Z",
            "user_create": 5,
            "user_update": null,
            "assemble_formulas": [
                {
                    "id": 85766,
                    "self_data_entries": [
                        {
                            "id": 168354,
                            "value": "15.00",
                            "data_entry": {
                                "id": 252,
                                "name": "Manga Candy",
                                "unit": {
                                    "id": 56,
                                    "name": "Gold2"
                                },
                                "dropdown": [
                                    {
                                        "name": "",
                                        "value": ""
                                    }
                                ],
                                "is_dropdown": false,
                                "is_material_selection": false,
                                "material_selections": [],
                                "created_date": "2024-01-29T02:56:06.660382Z",
                                "modified_date": "2024-01-29T02:56:06.660399Z",
                                "levels": [],
                                "material": {},
                                "default_column": {},
                                "content_type": 75,
                                "catalog": {},
                                "category": {}
                            },
                            "index": null,
                            "dropdown_value": {},
                            "material_value": {},
                            "nick_name": "Manga Candy",
                            "copies_from": null,
                            "group": "",
                            "material_data_entry_link": null,
                            "levels": [],
                            "is_client_view": true,
                            "po_group_index": 0,
                            "po_index": 0,
                            "custom_group_name": "Default",
                            "custom_group_index": 0,
                            "custom_index": 0,
                            "custom_po_index": 0,
                            "is_lock_estimate": false,
                            "is_lock_proposal": false,
                            "is_press_enter": false,
                            "default_value": "",
                            "default_dropdown_value": {},
                            "default_material_value": {},
                            "po_group_name": "New for"
                        },
                        {
                            "id": 168355,
                            "value": "",
                            "data_entry": {
                                "id": 469,
                                "name": "update data entry 2 2 1",
                                "unit": {
                                    "id": 325,
                                    "name": "cm"
                                },
                                "dropdown": [
                                    {
                                        "name": "",
                                        "value": ""
                                    }
                                ],
                                "is_dropdown": false,
                                "is_material_selection": false,
                                "material_selections": [],
                                "created_date": "2024-05-08T02:23:29.511197Z",
                                "modified_date": "2024-05-08T02:23:29.511223Z",
                                "levels": [],
                                "material": {},
                                "default_column": {},
                                "content_type": 75,
                                "catalog": {},
                                "category": {}
                            },
                            "index": null,
                            "dropdown_value": {
                                "id": 2,
                                "name": "value 2",
                                "value": "2"
                            },
                            "material_value": {},
                            "nick_name": "update data entry 2 2 1",
                            "copies_from": null,
                            "group": "",
                            "material_data_entry_link": null,
                            "levels": [],
                            "is_client_view": true,
                            "po_group_index": 0,
                            "po_index": 0,
                            "custom_group_name": "Default",
                            "custom_group_index": 0,
                            "custom_index": 0,
                            "custom_po_index": 0,
                            "is_lock_estimate": false,
                            "is_lock_proposal": false,
                            "is_press_enter": false,
                            "default_value": "",
                            "default_dropdown_value": {},
                            "default_material_value": {},
                            "po_group_name": "New for"
                        }
                    ],
                    "round_up": {
                        "type": "whole_number",
                        "whole_number": null,
                        "increments": [],
                        "last_action": "none",
                        "action_value": null
                    },
                    "created_date": "2024-05-31T07:25:19.495173Z",
                    "modified_date": "2024-05-31T07:25:19.495188Z",
                    "name": "New for",
                    "linked_description": [],
                    "formula": "update data entry 2 2  + Manga Candy",
                    "created_from": 47269,
                    "is_show": false,
                    "quantity": "17",
                    "markup": null,
                    "charge": "0",
                    "material": "{}",
                    "unit": "",
                    "unit_price": "0",
                    "cost": "0",
                    "total_cost": "0",
                    "margin": null,
                    "formula_mentions": "$[update data entry 2 2](469)  + $[Manga Candy](252)",
                    "formula_data_mentions": "",
                    "gross_profit": "",
                    "description_of_formula": "",
                    "formula_scenario": "",
                    "material_data_entry": {},
                    "formula_for_data_view": 42143,
                    "original": 47296,
                    "catalog_materials": [
                        {
                            "id": "",
                            "name": ""
                        }
                    ],
                    "order": 0,
                    "default_column": {},
                    "order_quantity": "17",
                    "selected_description": null,
                    "is_custom_po": false,
                    "user_create": 5,
                    "user_update": null,
                    "company": 1,
                    "group": null,
                    "assemble": 45642,
                    "content_type": 57,
                    "catalog_ancestor": null,
                    "catalog_link": [],
                    "material_value": {},
                    "status": true
                },
                {
                    "id": 85767,
                    "self_data_entries": [],
                    "round_up": {
                        "type": "whole_number",
                        "whole_number": null,
                        "increments": [],
                        "last_action": "none",
                        "action_value": null
                    },
                    "created_date": "2024-05-31T07:25:19.508641Z",
                    "modified_date": "2024-05-31T07:25:19.508656Z",
                    "name": "test 6 1 1 1",
                    "linked_description": [],
                    "formula": "",
                    "created_from": 39224,
                    "is_show": false,
                    "quantity": "0",
                    "markup": null,
                    "charge": "0",
                    "material": "{}",
                    "unit": "",
                    "unit_price": "0",
                    "cost": "0",
                    "total_cost": "0",
                    "margin": null,
                    "formula_mentions": "",
                    "formula_data_mentions": "",
                    "gross_profit": "",
                    "description_of_formula": "",
                    "formula_scenario": "",
                    "material_data_entry": {},
                    "formula_for_data_view": 39224,
                    "original": 39224,
                    "catalog_materials": [
                        null
                    ],
                    "order": 0,
                    "default_column": {},
                    "order_quantity": "0",
                    "selected_description": null,
                    "is_custom_po": false,
                    "user_create": 5,
                    "user_update": null,
                    "company": 1,
                    "group": null,
                    "assemble": 45642,
                    "content_type": 57,
                    "catalog_ancestor": null,
                    "catalog_link": [],
                    "material_value": {},
                    "status": false
                },
                {
                    "id": 85768,
                    "self_data_entries": [
                        {
                            "id": 168356,
                            "value": "",
                            "data_entry": {
                                "id": 441,
                                "name": "update data entry 2 1",
                                "unit": null,
                                "dropdown": [
                                    {
                                        "id": 1,
                                        "name": "tes",
                                        "value": "10"
                                    }
                                ],
                                "is_dropdown": true,
                                "is_material_selection": false,
                                "material_selections": [],
                                "created_date": "2024-04-15T09:34:05.554941Z",
                                "modified_date": "2024-04-15T09:34:05.554957Z",
                                "levels": [],
                                "material": {},
                                "default_column": {},
                                "content_type": 75,
                                "catalog": {},
                                "category": {}
                            },
                            "index": null,
                            "dropdown_value": {
                                "id": 1,
                                "name": "tes",
                                "value": "10"
                            },
                            "material_value": {},
                            "nick_name": "update data entry 2 1",
                            "copies_from": null,
                            "group": "",
                            "material_data_entry_link": null,
                            "levels": [],
                            "is_client_view": true,
                            "po_group_index": 0,
                            "po_index": 0,
                            "custom_group_name": "Default",
                            "custom_group_index": 0,
                            "custom_index": 0,
                            "custom_po_index": 0,
                            "is_lock_estimate": false,
                            "is_lock_proposal": false,
                            "is_press_enter": false,
                            "default_value": "",
                            "default_dropdown_value": {},
                            "default_material_value": {},
                            "po_group_name": "formula. qqq"
                        },
                        {
                            "id": 168357,
                            "value": "2.00",
                            "data_entry": {
                                "id": 469,
                                "name": "update data entry 2 2 1",
                                "unit": {
                                    "id": 325,
                                    "name": "cm"
                                },
                                "dropdown": [
                                    {
                                        "name": "",
                                        "value": ""
                                    }
                                ],
                                "is_dropdown": false,
                                "is_material_selection": false,
                                "material_selections": [],
                                "created_date": "2024-05-08T02:23:29.511197Z",
                                "modified_date": "2024-05-08T02:23:29.511223Z",
                                "levels": [],
                                "material": {},
                                "default_column": {},
                                "content_type": 75,
                                "catalog": {},
                                "category": {}
                            },
                            "index": null,
                            "dropdown_value": {},
                            "material_value": {},
                            "nick_name": "update data entry 2 2 1",
                            "copies_from": null,
                            "group": "",
                            "material_data_entry_link": null,
                            "levels": [],
                            "is_client_view": true,
                            "po_group_index": 0,
                            "po_index": 0,
                            "custom_group_name": "Default",
                            "custom_group_index": 0,
                            "custom_index": 0,
                            "custom_po_index": 0,
                            "is_lock_estimate": false,
                            "is_lock_proposal": false,
                            "is_press_enter": false,
                            "default_value": "",
                            "default_dropdown_value": {},
                            "default_material_value": {},
                            "po_group_name": "formula. qqq"
                        }
                    ],
                    "round_up": {
                        "type": "whole_number",
                        "whole_number": null,
                        "increments": [],
                        "last_action": "none",
                        "action_value": null
                    },
                    "created_date": "2024-05-31T07:25:19.520070Z",
                    "modified_date": "2024-05-31T07:25:19.520084Z",
                    "name": "formula. qqq",
                    "linked_description": [
                        {
                            "id": 3,
                            "name": "Cake",
                            "content_type": 81,
                            "created_date": "2023-06-21T02:51:20.327000Z",
                            "modified_date": "2023-06-21T02:51:20.327000Z",
                            "linked_description": "a sweet food made from a mixture of flour, eggs, butter, sugar, etc. that is baked in an oven."
                        },
                        {
                            "id": 1,
                            "name": "Rose",
                            "content_type": 81,
                            "created_date": "2023-05-30T09:49:19.322000Z",
                            "modified_date": "2023-05-30T09:55:05.956000Z",
                            "linked_description": "Roses have come to symbolise some of our strongest feelings, such as love, passion and admiration. Whether you want to express love, friendship, or joy, there's a rose for every emotion and occasion."
                        },
                        {
                            "id": 55,
                            "name": "Random",
                            "content_type": 81,
                            "created_date": "2024-03-12T04:05:09.342507Z",
                            "modified_date": "2024-03-12T04:05:09.342524Z",
                            "linked_description": "Random is random"
                        },
                        {
                            "id": 2,
                            "name": "Lavender",
                            "content_type": 81,
                            "created_date": "2023-05-30T09:54:55.686000Z",
                            "modified_date": "2023-05-30T09:54:55.686000Z",
                            "linked_description": "Lavender flowers represent purity, silence, devotion, serenity, grace, and calmness. Purple is the color of royalty and speaks of elegance, refinement, and luxury, too. The color is also associated with the crown chakra, which is the energy center associated with higher purpose and spiritual connectivity."
                        }
                    ],
                    "formula": "update data entry 2  + update data entry 2 1",
                    "created_from": 40840,
                    "is_show": false,
                    "quantity": "0",
                    "markup": "5",
                    "charge": "0",
                    "material": "{\"name\":\"Beloved\",\"unit\":\"Test 04\",\"cost\":88,\"Quantity\":\"4\",\"id\":\"13878:0\",\"levels\":[{\"id\":13874,\"name\":\"Wine\",\"level\":null,\"level_index\":0},{\"id\":13875,\"name\":\"Grape\",\"level\":null,\"level_index\":0},{\"id\":13876,\"name\":\"Chilly\",\"level\":985,\"level_index\":0},{\"id\":13877,\"name\":\"Jam\",\"level\":986,\"level_index\":1},{\"id\":13878,\"name\":\"trust\",\"level\":987,\"level_index\":2}],\"columns\":[{\"name\":\"name\",\"value\":\"Beloved\"},{\"name\":\"unit\",\"value\":\"Test 04\"},{\"name\":\"cost\",\"value\":\"88\"},{\"name\":\"Quantity\",\"value\":\"4\"}],\"default_column\":{\"id\":2,\"name\":\"cost\",\"value\":\"88\"}}",
                    "unit": "Test 04",
                    "unit_price": "92.4",
                    "cost": "88",
                    "total_cost": "0",
                    "margin": "0",
                    "formula_mentions": "$[update data entry 2](465)  + $[update data entry 2 1](441)",
                    "formula_data_mentions": "",
                    "gross_profit": "",
                    "description_of_formula": "<p>description of something abcd&nbsp;</p>",
                    "formula_scenario": "",
                    "material_data_entry": {},
                    "formula_for_data_view": 40840,
                    "original": 47294,
                    "catalog_materials": [
                        {
                            "id": 13874,
                            "name": "Wine",
                            "level": null,
                            "level_index": 0
                        },
                        {
                            "id": 13875,
                            "name": "Grape",
                            "level": null,
                            "level_index": 0
                        },
                        {
                            "id": 13876,
                            "name": "Chilly",
                            "level": 985,
                            "level_index": 0
                        },
                        {
                            "id": 13877,
                            "name": "Jam",
                            "level": 986,
                            "level_index": 1
                        },
                        {
                            "id": 13878,
                            "name": "trust",
                            "level": 987,
                            "level_index": 2
                        }
                    ],
                    "order": 0,
                    "default_column": {
                        "id": 2,
                        "name": "cost",
                        "value": "88"
                    },
                    "order_quantity": "0",
                    "selected_description": 3,
                    "is_custom_po": false,
                    "user_create": 5,
                    "user_update": null,
                    "company": 1,
                    "group": null,
                    "assemble": 45642,
                    "content_type": 57,
                    "catalog_ancestor": 13874,
                    "catalog_link": [
                        {
                            "id": 13874,
                            "name": "Wine",
                            "level": null,
                            "level_index": 0
                        },
                        {
                            "id": 13875,
                            "name": "Grape",
                            "level": null,
                            "level_index": 0
                        },
                        {
                            "id": 13876,
                            "name": "Chilly",
                            "level": 985,
                            "level_index": 0
                        },
                        {
                            "id": 13877,
                            "name": "Jam",
                            "level": 986,
                            "level_index": 1
                        },
                        {
                            "id": 13878,
                            "name": "trust",
                            "level": 987,
                            "level_index": 2
                        }
                    ],
                    "material_value": {
                        "name": "Beloved",
                        "unit": "Test 04",
                        "cost": "88",
                        "Quantity": "4",
                        "id": "13878:0",
                        "levels": [
                            {
                                "id": 13874,
                                "name": "Wine",
                                "level": null,
                                "level_index": 0
                            },
                            {
                                "id": 13875,
                                "name": "Grape",
                                "level": null,
                                "level_index": 0
                            },
                            {
                                "id": 13876,
                                "name": "Chilly",
                                "level": 985,
                                "level_index": 0
                            },
                            {
                                "id": 13877,
                                "name": "Jam",
                                "level": 986,
                                "level_index": 1
                            },
                            {
                                "id": 13878,
                                "name": "trust",
                                "level": 987,
                                "level_index": 2
                            }
                        ],
                        "columns": [
                            {
                                "name": "name",
                                "value": "Beloved"
                            },
                            {
                                "name": "unit",
                                "value": "Test 04"
                            },
                            {
                                "name": "cost",
                                "value": "88"
                            },
                            {
                                "name": "Quantity",
                                "value": "4"
                            }
                        ],
                        "default_column": {
                            "id": 2,
                            "name": "cost",
                            "value": "88"
                        }
                    },
                    "status": true
                }
            ],
            "description": "",
            "is_show": false,
            "original": 24982,
            "is_custom_assemble": false,
            "content_type": 82
        },
        {
            "id": 45643,
            "name": "new as",
            "created_date": "2024-05-31T07:25:19.538609Z",
            "modified_date": "2024-05-31T07:25:19.538623Z",
            "user_create": 5,
            "user_update": null,
            "assemble_formulas": [
                {
                    "id": 85769,
                    "self_data_entries": [
                        {
                            "id": 168358,
                            "value": "15.00",
                            "data_entry": {
                                "id": 252,
                                "name": "Manga Candy",
                                "unit": {
                                    "id": 56,
                                    "name": "Gold2"
                                },
                                "dropdown": [
                                    {
                                        "name": "",
                                        "value": ""
                                    }
                                ],
                                "is_dropdown": false,
                                "is_material_selection": false,
                                "material_selections": [],
                                "created_date": "2024-01-29T02:56:06.660382Z",
                                "modified_date": "2024-01-29T02:56:06.660399Z",
                                "levels": [],
                                "material": {},
                                "default_column": {},
                                "content_type": 75,
                                "catalog": {},
                                "category": {}
                            },
                            "index": null,
                            "dropdown_value": {},
                            "material_value": {},
                            "nick_name": "Manga Candy",
                            "copies_from": null,
                            "group": "",
                            "material_data_entry_link": null,
                            "levels": [],
                            "is_client_view": true,
                            "po_group_index": 0,
                            "po_index": 0,
                            "custom_group_name": "Default",
                            "custom_group_index": 0,
                            "custom_index": 0,
                            "custom_po_index": 0,
                            "is_lock_estimate": false,
                            "is_lock_proposal": false,
                            "is_press_enter": false,
                            "default_value": "",
                            "default_dropdown_value": {},
                            "default_material_value": {},
                            "po_group_name": "New for"
                        },
                        {
                            "id": 168359,
                            "value": "",
                            "data_entry": {
                                "id": 469,
                                "name": "update data entry 2 2 1",
                                "unit": {
                                    "id": 325,
                                    "name": "cm"
                                },
                                "dropdown": [
                                    {
                                        "name": "",
                                        "value": ""
                                    }
                                ],
                                "is_dropdown": false,
                                "is_material_selection": false,
                                "material_selections": [],
                                "created_date": "2024-05-08T02:23:29.511197Z",
                                "modified_date": "2024-05-08T02:23:29.511223Z",
                                "levels": [],
                                "material": {},
                                "default_column": {},
                                "content_type": 75,
                                "catalog": {},
                                "category": {}
                            },
                            "index": null,
                            "dropdown_value": {
                                "id": 2,
                                "name": "value 2",
                                "value": "2"
                            },
                            "material_value": {},
                            "nick_name": "update data entry 2 2 1",
                            "copies_from": null,
                            "group": "",
                            "material_data_entry_link": null,
                            "levels": [],
                            "is_client_view": true,
                            "po_group_index": 0,
                            "po_index": 0,
                            "custom_group_name": "Default",
                            "custom_group_index": 0,
                            "custom_index": 0,
                            "custom_po_index": 0,
                            "is_lock_estimate": false,
                            "is_lock_proposal": false,
                            "is_press_enter": false,
                            "default_value": "",
                            "default_dropdown_value": {},
                            "default_material_value": {},
                            "po_group_name": "New for"
                        }
                    ],
                    "round_up": {
                        "type": "whole_number",
                        "whole_number": null,
                        "increments": [],
                        "last_action": "none",
                        "action_value": null
                    },
                    "created_date": "2024-05-31T07:25:19.551190Z",
                    "modified_date": "2024-05-31T07:25:19.551205Z",
                    "name": "New for",
                    "linked_description": [],
                    "formula": "update data entry 2 2  + Manga Candy",
                    "created_from": 47267,
                    "is_show": false,
                    "quantity": "17",
                    "markup": null,
                    "charge": "0",
                    "material": "{}",
                    "unit": "",
                    "unit_price": "0",
                    "cost": "0",
                    "total_cost": "0",
                    "margin": null,
                    "formula_mentions": "$[update data entry 2 2](469)  + $[Manga Candy](252)",
                    "formula_data_mentions": "",
                    "gross_profit": "",
                    "description_of_formula": "",
                    "formula_scenario": "",
                    "material_data_entry": {},
                    "formula_for_data_view": 42139,
                    "original": 47296,
                    "catalog_materials": [
                        {
                            "id": "",
                            "name": ""
                        }
                    ],
                    "order": 0,
                    "default_column": {},
                    "order_quantity": "17",
                    "selected_description": null,
                    "is_custom_po": false,
                    "user_create": 5,
                    "user_update": null,
                    "company": 1,
                    "group": null,
                    "assemble": 45643,
                    "content_type": 57,
                    "catalog_ancestor": null,
                    "catalog_link": [],
                    "material_value": {},
                    "status": true
                }
            ],
            "description": "",
            "is_show": false,
            "original": 24981,
            "is_custom_assemble": false,
            "content_type": 82
        },
        {
            "id": 45644,
            "name": "123 2 co description",
            "created_date": "2024-05-31T07:25:19.579103Z",
            "modified_date": "2024-05-31T07:25:19.579119Z",
            "user_create": 5,
            "user_update": null,
            "assemble_formulas": [
                {
                    "id": 85770,
                    "self_data_entries": [],
                    "round_up": {
                        "type": "whole_number",
                        "whole_number": null,
                        "increments": [],
                        "last_action": "none",
                        "action_value": null
                    },
                    "created_date": "2024-05-31T07:25:19.584613Z",
                    "modified_date": "2024-05-31T07:25:19.584629Z",
                    "name": "test 6 1 1 1",
                    "linked_description": [],
                    "formula": "",
                    "created_from": 39224,
                    "is_show": false,
                    "quantity": "0",
                    "markup": null,
                    "charge": "0",
                    "material": "{}",
                    "unit": "",
                    "unit_price": "0",
                    "cost": "0",
                    "total_cost": "0",
                    "margin": null,
                    "formula_mentions": "",
                    "formula_data_mentions": "",
                    "gross_profit": "",
                    "description_of_formula": "",
                    "formula_scenario": "",
                    "material_data_entry": {},
                    "formula_for_data_view": 39224,
                    "original": 39224,
                    "catalog_materials": [
                        null
                    ],
                    "order": 0,
                    "default_column": {},
                    "order_quantity": "0",
                    "selected_description": null,
                    "is_custom_po": false,
                    "user_create": 5,
                    "user_update": null,
                    "company": 1,
                    "group": null,
                    "assemble": 45644,
                    "content_type": 57,
                    "catalog_ancestor": null,
                    "catalog_link": [],
                    "material_value": {},
                    "status": false
                },
                {
                    "id": 85771,
                    "self_data_entries": [
                        {
                            "id": 168360,
                            "value": "15.00",
                            "data_entry": {
                                "id": 252,
                                "name": "Manga Candy",
                                "unit": {
                                    "id": 56,
                                    "name": "Gold2"
                                },
                                "dropdown": [
                                    {
                                        "name": "",
                                        "value": ""
                                    }
                                ],
                                "is_dropdown": false,
                                "is_material_selection": false,
                                "material_selections": [],
                                "created_date": "2024-01-29T02:56:06.660382Z",
                                "modified_date": "2024-01-29T02:56:06.660399Z",
                                "levels": [],
                                "material": {},
                                "default_column": {},
                                "content_type": 75,
                                "catalog": {},
                                "category": {}
                            },
                            "index": null,
                            "dropdown_value": {},
                            "material_value": {},
                            "nick_name": "Manga Candy",
                            "copies_from": null,
                            "group": "",
                            "material_data_entry_link": null,
                            "levels": [],
                            "is_client_view": true,
                            "po_group_index": 0,
                            "po_index": 0,
                            "custom_group_name": "Default",
                            "custom_group_index": 0,
                            "custom_index": 0,
                            "custom_po_index": 0,
                            "is_lock_estimate": false,
                            "is_lock_proposal": false,
                            "is_press_enter": false,
                            "default_value": "",
                            "default_dropdown_value": {},
                            "default_material_value": {},
                            "po_group_name": "New for"
                        },
                        {
                            "id": 168361,
                            "value": "",
                            "data_entry": {
                                "id": 468,
                                "name": "update data entry 2 2",
                                "unit": {
                                    "id": 325,
                                    "name": "cm"
                                },
                                "dropdown": [
                                    {
                                        "name": "",
                                        "value": ""
                                    }
                                ],
                                "is_dropdown": false,
                                "is_material_selection": false,
                                "material_selections": [],
                                "created_date": "2024-05-08T02:22:57.976983Z",
                                "modified_date": "2024-05-08T02:22:57.976999Z",
                                "levels": [],
                                "material": {},
                                "default_column": {},
                                "content_type": 75,
                                "catalog": {},
                                "category": {}
                            },
                            "index": null,
                            "dropdown_value": {
                                "id": 2,
                                "name": "value 2",
                                "value": "2"
                            },
                            "material_value": {},
                            "nick_name": "update data entry 2 2",
                            "copies_from": null,
                            "group": "",
                            "material_data_entry_link": null,
                            "levels": [],
                            "is_client_view": true,
                            "po_group_index": 0,
                            "po_index": 0,
                            "custom_group_name": "Default",
                            "custom_group_index": 0,
                            "custom_index": 0,
                            "custom_po_index": 0,
                            "is_lock_estimate": false,
                            "is_lock_proposal": false,
                            "is_press_enter": false,
                            "default_value": "",
                            "default_dropdown_value": {},
                            "default_material_value": {},
                            "po_group_name": "New for"
                        }
                    ],
                    "round_up": {
                        "type": "whole_number",
                        "whole_number": null,
                        "increments": [],
                        "last_action": "none",
                        "action_value": null
                    },
                    "created_date": "2024-05-31T07:25:19.597299Z",
                    "modified_date": "2024-05-31T07:25:19.597315Z",
                    "name": "New for",
                    "linked_description": [],
                    "formula": "update data entry 2 2  + Manga Candy",
                    "created_from": 47269,
                    "is_show": false,
                    "quantity": "17",
                    "markup": null,
                    "charge": "0",
                    "material": "{}",
                    "unit": "",
                    "unit_price": "0",
                    "cost": "0",
                    "total_cost": "0",
                    "margin": null,
                    "formula_mentions": "$[update data entry 2 2](468)  + $[Manga Candy](252)",
                    "formula_data_mentions": "",
                    "gross_profit": "",
                    "description_of_formula": "",
                    "formula_scenario": "",
                    "material_data_entry": {},
                    "formula_for_data_view": 42143,
                    "original": 47281,
                    "catalog_materials": [
                        {
                            "id": "",
                            "name": ""
                        }
                    ],
                    "order": 0,
                    "default_column": {},
                    "order_quantity": "17",
                    "selected_description": null,
                    "is_custom_po": false,
                    "user_create": 5,
                    "user_update": null,
                    "company": 1,
                    "group": null,
                    "assemble": 45644,
                    "content_type": 57,
                    "catalog_ancestor": null,
                    "catalog_link": [],
                    "material_value": {},
                    "status": true
                },
                {
                    "id": 85772,
                    "self_data_entries": [
                        {
                            "id": 168362,
                            "value": "",
                            "data_entry": {
                                "id": 441,
                                "name": "update data entry 2 1",
                                "unit": null,
                                "dropdown": [
                                    {
                                        "id": 1,
                                        "name": "tes",
                                        "value": "10"
                                    }
                                ],
                                "is_dropdown": true,
                                "is_material_selection": false,
                                "material_selections": [],
                                "created_date": "2024-04-15T09:34:05.554941Z",
                                "modified_date": "2024-04-15T09:34:05.554957Z",
                                "levels": [],
                                "material": {},
                                "default_column": {},
                                "content_type": 75,
                                "catalog": {},
                                "category": {}
                            },
                            "index": null,
                            "dropdown_value": {
                                "id": 1,
                                "name": "tes",
                                "value": "10"
                            },
                            "material_value": {},
                            "nick_name": "update data entry 2 1",
                            "copies_from": null,
                            "group": "",
                            "material_data_entry_link": null,
                            "levels": [],
                            "is_client_view": true,
                            "po_group_index": 0,
                            "po_index": 0,
                            "custom_group_name": "Default",
                            "custom_group_index": 0,
                            "custom_index": 0,
                            "custom_po_index": 0,
                            "is_lock_estimate": false,
                            "is_lock_proposal": false,
                            "is_press_enter": false,
                            "default_value": "",
                            "default_dropdown_value": {},
                            "default_material_value": {},
                            "po_group_name": "formula. qqq"
                        },
                        {
                            "id": 168363,
                            "value": "2.00",
                            "data_entry": {
                                "id": 468,
                                "name": "update data entry 2 2",
                                "unit": {
                                    "id": 325,
                                    "name": "cm"
                                },
                                "dropdown": [
                                    {
                                        "name": "",
                                        "value": ""
                                    }
                                ],
                                "is_dropdown": false,
                                "is_material_selection": false,
                                "material_selections": [],
                                "created_date": "2024-05-08T02:22:57.976983Z",
                                "modified_date": "2024-05-08T02:22:57.976999Z",
                                "levels": [],
                                "material": {},
                                "default_column": {},
                                "content_type": 75,
                                "catalog": {},
                                "category": {}
                            },
                            "index": null,
                            "dropdown_value": {},
                            "material_value": {},
                            "nick_name": "update data entry 2 2",
                            "copies_from": null,
                            "group": "",
                            "material_data_entry_link": null,
                            "levels": [],
                            "is_client_view": true,
                            "po_group_index": 0,
                            "po_index": 0,
                            "custom_group_name": "Default",
                            "custom_group_index": 0,
                            "custom_index": 0,
                            "custom_po_index": 0,
                            "is_lock_estimate": false,
                            "is_lock_proposal": false,
                            "is_press_enter": false,
                            "default_value": "",
                            "default_dropdown_value": {},
                            "default_material_value": {},
                            "po_group_name": "formula. qqq"
                        }
                    ],
                    "round_up": {
                        "type": "whole_number",
                        "whole_number": null,
                        "increments": [],
                        "last_action": "none",
                        "action_value": null
                    },
                    "created_date": "2024-05-31T07:25:19.618144Z",
                    "modified_date": "2024-05-31T07:25:19.618159Z",
                    "name": "formula. qqq",
                    "linked_description": [
                        {
                            "id": 3,
                            "name": "Cake",
                            "content_type": 81,
                            "created_date": "2023-06-21T02:51:20.327000Z",
                            "modified_date": "2023-06-21T02:51:20.327000Z",
                            "linked_description": "a sweet food made from a mixture of flour, eggs, butter, sugar, etc. that is baked in an oven."
                        },
                        {
                            "id": 1,
                            "name": "Rose",
                            "content_type": 81,
                            "created_date": "2023-05-30T09:49:19.322000Z",
                            "modified_date": "2023-05-30T09:55:05.956000Z",
                            "linked_description": "Roses have come to symbolise some of our strongest feelings, such as love, passion and admiration. Whether you want to express love, friendship, or joy, there's a rose for every emotion and occasion."
                        },
                        {
                            "id": 55,
                            "name": "Random",
                            "content_type": 81,
                            "created_date": "2024-03-12T04:05:09.342507Z",
                            "modified_date": "2024-03-12T04:05:09.342524Z",
                            "linked_description": "Random is random"
                        },
                        {
                            "id": 2,
                            "name": "Lavender",
                            "content_type": 81,
                            "created_date": "2023-05-30T09:54:55.686000Z",
                            "modified_date": "2023-05-30T09:54:55.686000Z",
                            "linked_description": "Lavender flowers represent purity, silence, devotion, serenity, grace, and calmness. Purple is the color of royalty and speaks of elegance, refinement, and luxury, too. The color is also associated with the crown chakra, which is the energy center associated with higher purpose and spiritual connectivity."
                        }
                    ],
                    "formula": "update data entry 2  + update data entry 2 1",
                    "created_from": 40840,
                    "is_show": false,
                    "quantity": "0",
                    "markup": "5",
                    "charge": "0",
                    "material": "{\"name\":\"Beloved\",\"unit\":\"Test 04\",\"cost\":88,\"Quantity\":\"4\",\"id\":\"13878:0\",\"levels\":[{\"id\":13874,\"name\":\"Wine\",\"level\":null,\"level_index\":0},{\"id\":13875,\"name\":\"Grape\",\"level\":null,\"level_index\":0},{\"id\":13876,\"name\":\"Chilly\",\"level\":985,\"level_index\":0},{\"id\":13877,\"name\":\"Jam\",\"level\":986,\"level_index\":1},{\"id\":13878,\"name\":\"trust\",\"level\":987,\"level_index\":2}],\"columns\":[{\"name\":\"name\",\"value\":\"Beloved\"},{\"name\":\"unit\",\"value\":\"Test 04\"},{\"name\":\"cost\",\"value\":\"88\"},{\"name\":\"Quantity\",\"value\":\"4\"}],\"default_column\":{\"id\":2,\"name\":\"cost\",\"value\":\"88\"}}",
                    "unit": "Test 04",
                    "unit_price": "92.4",
                    "cost": "88",
                    "total_cost": "0",
                    "margin": "0",
                    "formula_mentions": "$[update data entry 2](465)  + $[update data entry 2 1](441)",
                    "formula_data_mentions": "",
                    "gross_profit": "",
                    "description_of_formula": "<p>description of something abcd&nbsp;</p>",
                    "formula_scenario": "",
                    "material_data_entry": {},
                    "formula_for_data_view": 40840,
                    "original": 47279,
                    "catalog_materials": [
                        {
                            "id": 13874,
                            "name": "Wine",
                            "level": null,
                            "level_index": 0
                        },
                        {
                            "id": 13875,
                            "name": "Grape",
                            "level": null,
                            "level_index": 0
                        },
                        {
                            "id": 13876,
                            "name": "Chilly",
                            "level": 985,
                            "level_index": 0
                        },
                        {
                            "id": 13877,
                            "name": "Jam",
                            "level": 986,
                            "level_index": 1
                        },
                        {
                            "id": 13878,
                            "name": "trust",
                            "level": 987,
                            "level_index": 2
                        }
                    ],
                    "order": 0,
                    "default_column": {
                        "id": 2,
                        "name": "cost",
                        "value": "88"
                    },
                    "order_quantity": "0",
                    "selected_description": 3,
                    "is_custom_po": false,
                    "user_create": 5,
                    "user_update": null,
                    "company": 1,
                    "group": null,
                    "assemble": 45644,
                    "content_type": 57,
                    "catalog_ancestor": 13874,
                    "catalog_link": [
                        {
                            "id": 13874,
                            "name": "Wine",
                            "level": null,
                            "level_index": 0
                        },
                        {
                            "id": 13875,
                            "name": "Grape",
                            "level": null,
                            "level_index": 0
                        },
                        {
                            "id": 13876,
                            "name": "Chilly",
                            "level": 985,
                            "level_index": 0
                        },
                        {
                            "id": 13877,
                            "name": "Jam",
                            "level": 986,
                            "level_index": 1
                        },
                        {
                            "id": 13878,
                            "name": "trust",
                            "level": 987,
                            "level_index": 2
                        }
                    ],
                    "material_value": {
                        "name": "Beloved",
                        "unit": "Test 04",
                        "cost": "88",
                        "Quantity": "4",
                        "id": "13878:0",
                        "levels": [
                            {
                                "id": 13874,
                                "name": "Wine",
                                "level": null,
                                "level_index": 0
                            },
                            {
                                "id": 13875,
                                "name": "Grape",
                                "level": null,
                                "level_index": 0
                            },
                            {
                                "id": 13876,
                                "name": "Chilly",
                                "level": 985,
                                "level_index": 0
                            },
                            {
                                "id": 13877,
                                "name": "Jam",
                                "level": 986,
                                "level_index": 1
                            },
                            {
                                "id": 13878,
                                "name": "trust",
                                "level": 987,
                                "level_index": 2
                            }
                        ],
                        "columns": [
                            {
                                "name": "name",
                                "value": "Beloved"
                            },
                            {
                                "name": "unit",
                                "value": "Test 04"
                            },
                            {
                                "name": "cost",
                                "value": "88"
                            },
                            {
                                "name": "Quantity",
                                "value": "4"
                            }
                        ],
                        "default_column": {
                            "id": 2,
                            "name": "cost",
                            "value": "88"
                        }
                    },
                    "status": true
                }
            ],
            "description": "",
            "is_show": false,
            "original": 24976,
            "is_custom_assemble": false,
            "content_type": 82
        }
    ],
    "data_views": [
        {
            "id": 81594,
            "formula": "(@[testing for scott](testing for scott)__[Testing for Scott](Testing for Scott)__[Charge](charge) + @[Using For 2 Onlu](Using For 2 Onlu)__[For 2 1](For 2 1)__[Charge](charge) + @[this use entries 1 and enstries 2](this use entries 1 and enstries 2)__[this have 2 data entries](this have 2 data entries)__[Charge](charge) + @[this also use entries 1 and 2](this also use entries 1 and 2)__[this use 2 data entries with 1](this use 2 data entries with 1)__[Charge](charge) + @[L'sn 222](L'sn 222)__[update empty data entry 2 (2)](update empty data entry 2 (2))__[Charge](charge) + @[L'sn 222](L'sn 222)__[update empty data entry 2 (2)](update empty data entry 2 (2))__[Charge](charge) + @[Assembly with empty formula](Assembly with empty formula)__[empty formula](empty formula)__[Charge](charge) + @[123 2 co description 1](123 2 co description 1)__[test 6 1 1 1](test 6 1 1 1)__[Charge](charge) + @[123 2 co description 1](123 2 co description 1)__[New for](New for)__[Charge](charge) + @[123 2 co description 1](123 2 co description 1)__[formula. qqq](formula. qqq)__[Charge](charge) + @[new as](new as)__[New for](New for)__[Charge](charge) + @[123 2 co description](123 2 co description)__[test 6 1 1 1](test 6 1 1 1)__[Charge](charge) + @[123 2 co description](123 2 co description)__[New for](New for)__[Charge](charge) + @[123 2 co description](123 2 co description)__[formula. qqq](formula. qqq)__[Charge](charge)) - (@[testing for scott](testing for scott)__[Testing for Scott](Testing for Scott)__[Total_Cost](total_cost) + @[Using For 2 Onlu](Using For 2 Onlu)__[For 2 1](For 2 1)__[Total_Cost](total_cost) + @[this use entries 1 and enstries 2](this use entries 1 and enstries 2)__[this have 2 data entries](this have 2 data entries)__[Total_Cost](total_cost) + @[this also use entries 1 and 2](this also use entries 1 and 2)__[this use 2 data entries with 1](this use 2 data entries with 1)__[Total_Cost](total_cost) + @[L'sn 222](L'sn 222)__[update empty data entry 2 (2)](update empty data entry 2 (2))__[Total_Cost](total_cost) + @[L'sn 222](L'sn 222)__[update empty data entry 2 (2)](update empty data entry 2 (2))__[Total_Cost](total_cost) + @[Assembly with empty formula](Assembly with empty formula)__[empty formula](empty formula)__[Total_Cost](total_cost) + @[123 2 co description 1](123 2 co description 1)__[test 6 1 1 1](test 6 1 1 1)__[Total_Cost](total_cost) + @[123 2 co description 1](123 2 co description 1)__[New for](New for)__[Total_Cost](total_cost) + @[123 2 co description 1](123 2 co description 1)__[formula. qqq](formula. qqq)__[Total_Cost](total_cost) + @[new as](new as)__[New for](New for)__[Total_Cost](total_cost) + @[123 2 co description](123 2 co description)__[test 6 1 1 1](test 6 1 1 1)__[Total_Cost](total_cost) + @[123 2 co description](123 2 co description)__[New for](New for)__[Total_Cost](total_cost) + @[123 2 co description](123 2 co description)__[formula. qqq](formula. qqq)__[Total_Cost](total_cost))",
            "name": "Gross Profit",
            "estimate_template": 24415,
            "type": "profit",
            "is_client_view": false,
            "unit": null,
            "result": null
        },
        {
            "id": 81595,
            "formula": "@[testing for scott](testing for scott)__[Testing for Scott](Testing for Scott)__[Total_Cost](total_cost) + @[Using For 2 Onlu](Using For 2 Onlu)__[For 2 1](For 2 1)__[Total_Cost](total_cost) + @[this use entries 1 and enstries 2](this use entries 1 and enstries 2)__[this have 2 data entries](this have 2 data entries)__[Total_Cost](total_cost) + @[this also use entries 1 and 2](this also use entries 1 and 2)__[this use 2 data entries with 1](this use 2 data entries with 1)__[Total_Cost](total_cost) + @[L'sn 222](L'sn 222)__[update empty data entry 2 (2)](update empty data entry 2 (2))__[Total_Cost](total_cost) + @[L'sn 222](L'sn 222)__[update empty data entry 2 (2)](update empty data entry 2 (2))__[Total_Cost](total_cost) + @[Assembly with empty formula](Assembly with empty formula)__[empty formula](empty formula)__[Total_Cost](total_cost) + @[123 2 co description 1](123 2 co description 1)__[test 6 1 1 1](test 6 1 1 1)__[Total_Cost](total_cost) + @[123 2 co description 1](123 2 co description 1)__[New for](New for)__[Total_Cost](total_cost) + @[123 2 co description 1](123 2 co description 1)__[formula. qqq](formula. qqq)__[Total_Cost](total_cost) + @[new as](new as)__[New for](New for)__[Total_Cost](total_cost) + @[123 2 co description](123 2 co description)__[test 6 1 1 1](test 6 1 1 1)__[Total_Cost](total_cost) + @[123 2 co description](123 2 co description)__[New for](New for)__[Total_Cost](total_cost) + @[123 2 co description](123 2 co description)__[formula. qqq](formula. qqq)__[Total_Cost](total_cost)",
            "name": "Total Cost",
            "estimate_template": 24415,
            "type": "cost",
            "is_client_view": false,
            "unit": null,
            "result": null
        },
        {
            "id": 81596,
            "formula": "@[testing for scott](testing for scott)__[Testing for Scott](Testing for Scott)__[Charge](charge) + @[Using For 2 Onlu](Using For 2 Onlu)__[For 2 1](For 2 1)__[Charge](charge) + @[this use entries 1 and enstries 2](this use entries 1 and enstries 2)__[this have 2 data entries](this have 2 data entries)__[Charge](charge) + @[this also use entries 1 and 2](this also use entries 1 and 2)__[this use 2 data entries with 1](this use 2 data entries with 1)__[Charge](charge) + @[L'sn 222](L'sn 222)__[update empty data entry 2 (2)](update empty data entry 2 (2))__[Charge](charge) + @[L'sn 222](L'sn 222)__[update empty data entry 2 (2)](update empty data entry 2 (2))__[Charge](charge) + @[Assembly with empty formula](Assembly with empty formula)__[empty formula](empty formula)__[Charge](charge) + @[123 2 co description 1](123 2 co description 1)__[test 6 1 1 1](test 6 1 1 1)__[Charge](charge) + @[123 2 co description 1](123 2 co description 1)__[New for](New for)__[Charge](charge) + @[123 2 co description 1](123 2 co description 1)__[formula. qqq](formula. qqq)__[Charge](charge) + @[new as](new as)__[New for](New for)__[Charge](charge) + @[123 2 co description](123 2 co description)__[test 6 1 1 1](test 6 1 1 1)__[Charge](charge) + @[123 2 co description](123 2 co description)__[New for](New for)__[Charge](charge) + @[123 2 co description](123 2 co description)__[formula. qqq](formula. qqq)__[Charge](charge)",
            "name": "Total Charge",
            "estimate_template": 24415,
            "type": "charge",
            "is_client_view": false,
            "unit": null,
            "result": "0"
        }
    ],
    "data_entries": [
        {
            "id": 168319,
            "value": "2.00",
            "data_entry": {
                "id": 468,
                "name": "update data entry 2 2",
                "unit": {
                    "id": 325,
                    "name": "cm"
                },
                "dropdown": [
                    {
                        "name": "",
                        "value": ""
                    }
                ],
                "is_dropdown": false,
                "is_material_selection": false,
                "material_selections": [],
                "created_date": "2024-05-08T02:22:57.976983Z",
                "modified_date": "2024-05-08T02:22:57.976999Z",
                "levels": [],
                "material": {},
                "default_column": {},
                "content_type": 75,
                "catalog": {},
                "category": {}
            },
            "index": null,
            "dropdown_value": {},
            "material_value": {},
            "nick_name": "update data entry 2 2",
            "copies_from": [
                {
                    "id": 79241,
                    "formula": 40840,
                    "data_entry": 468,
                    "formula_name": "formula. qqq"
                }
            ],
            "group": "",
            "material_data_entry_link": null,
            "levels": [],
            "is_client_view": true,
            "po_group_index": 0,
            "po_index": 0,
            "custom_group_name": "Default",
            "custom_group_index": 0,
            "custom_index": 14,
            "custom_po_index": 0,
            "is_lock_estimate": false,
            "is_lock_proposal": false,
            "is_press_enter": false,
            "default_value": "2.00",
            "default_dropdown_value": {},
            "default_material_value": {},
            "po_group_name": "formula. qqq"
        },
        {
            "id": 168320,
            "value": "12.00",
            "data_entry": {
                "id": 12,
                "name": "Gold",
                "unit": {
                    "id": 12,
                    "name": "Gold"
                },
                "dropdown": [
                    {
                        "name": "",
                        "value": ""
                    }
                ],
                "is_dropdown": false,
                "is_material_selection": false,
                "material_selections": [],
                "created_date": "2023-06-16T07:02:37.498000Z",
                "modified_date": "2023-06-16T07:02:37.498000Z",
                "levels": [],
                "material": {},
                "default_column": {
                    "name": "cost",
                    "value": 0
                },
                "content_type": 75,
                "catalog": {},
                "category": {}
            },
            "index": null,
            "dropdown_value": {},
            "material_value": {},
            "nick_name": "Gold",
            "copies_from": [
                {
                    "id": 160952,
                    "formula": 83176,
                    "data_entry": 12,
                    "formula_name": "For 2 1"
                }
            ],
            "group": "",
            "material_data_entry_link": null,
            "levels": [],
            "is_client_view": true,
            "po_group_index": 0,
            "po_index": 0,
            "custom_group_name": "New Group",
            "custom_group_index": 1,
            "custom_index": 0,
            "custom_po_index": 0,
            "is_lock_estimate": false,
            "is_lock_proposal": false,
            "is_press_enter": false,
            "default_value": "12.00",
            "default_dropdown_value": {},
            "default_material_value": {},
            "po_group_name": "For 2 1"
        },
        {
            "id": 168321,
            "value": "",
            "data_entry": {
                "id": 472,
                "name": "entries 1",
                "unit": null,
                "dropdown": [
                    {
                        "id": 1,
                        "name": "abc",
                        "value": "12"
                    }
                ],
                "is_dropdown": true,
                "is_material_selection": false,
                "material_selections": [],
                "created_date": "2024-05-08T02:25:55.792811Z",
                "modified_date": "2024-05-08T02:25:55.792831Z",
                "levels": [],
                "material": {},
                "default_column": {},
                "content_type": 75,
                "catalog": {},
                "category": {}
            },
            "index": null,
            "dropdown_value": {
                "id": 1,
                "name": "abc",
                "value": "12"
            },
            "material_value": {},
            "nick_name": "entries 1",
            "copies_from": [
                {
                    "id": 160864,
                    "formula": 83163,
                    "data_entry": 472,
                    "formula_name": "this have 2 data entries"
                }
            ],
            "group": "",
            "material_data_entry_link": null,
            "levels": [],
            "is_client_view": true,
            "po_group_index": 0,
            "po_index": 0,
            "custom_group_name": "New Group",
            "custom_group_index": 1,
            "custom_index": 1,
            "custom_po_index": 0,
            "is_lock_estimate": false,
            "is_lock_proposal": false,
            "is_press_enter": false,
            "default_value": "",
            "default_dropdown_value": {
                "id": 1,
                "name": "abc",
                "value": "12"
            },
            "default_material_value": {},
            "po_group_name": "this have 2 data entries"
        },
        {
            "id": 168322,
            "value": "",
            "data_entry": {
                "id": 380,
                "name": "2.00",
                "unit": {
                    "id": 232,
                    "name": "box"
                },
                "dropdown": [
                    {
                        "name": "",
                        "value": ""
                    }
                ],
                "is_dropdown": false,
                "is_material_selection": false,
                "material_selections": [],
                "created_date": "2024-04-02T04:44:05.350112Z",
                "modified_date": "2024-04-02T04:44:05.350131Z",
                "levels": [],
                "material": {},
                "default_column": {},
                "content_type": 75,
                "catalog": {},
                "category": {}
            },
            "index": null,
            "dropdown_value": {},
            "material_value": {},
            "nick_name": "2.00",
            "copies_from": [
                {
                    "id": 160868,
                    "formula": 83163,
                    "data_entry": 380,
                    "formula_name": "this have 2 data entries"
                }
            ],
            "group": "",
            "material_data_entry_link": null,
            "levels": [],
            "is_client_view": true,
            "po_group_index": 0,
            "po_index": 0,
            "custom_group_name": "Default",
            "custom_group_index": 0,
            "custom_index": 0,
            "custom_po_index": 0,
            "is_lock_estimate": false,
            "is_lock_proposal": false,
            "is_press_enter": false,
            "default_value": "",
            "default_dropdown_value": {},
            "default_material_value": {},
            "po_group_name": "this have 2 data entries"
        },
        {
            "id": 168323,
            "value": "",
            "data_entry": {
                "id": 322,
                "name": "Track Loader?",
                "unit": null,
                "dropdown": [
                    {
                        "id": 1,
                        "name": "Yes Large ",
                        "value": "0.20"
                    },
                    {
                        "id": 2,
                        "name": "Yes Medium",
                        "value": "0.40"
                    },
                    {
                        "id": 3,
                        "name": "Yes Small ",
                        "value": "0.60"
                    },
                    {
                        "id": 4,
                        "name": "No",
                        "value": "1"
                    }
                ],
                "is_dropdown": true,
                "is_material_selection": false,
                "material_selections": [],
                "created_date": "2024-03-19T23:13:21.482696Z",
                "modified_date": "2024-03-19T23:13:21.482715Z",
                "levels": [],
                "material": {},
                "default_column": {},
                "content_type": 75,
                "catalog": {},
                "category": {}
            },
            "index": null,
            "dropdown_value": {},
            "material_value": {},
            "nick_name": "Track Loader?",
            "copies_from": [
                {
                    "id": 160869,
                    "formula": 83163,
                    "data_entry": 322,
                    "formula_name": "this have 2 data entries"
                }
            ],
            "group": "",
            "material_data_entry_link": null,
            "levels": [],
            "is_client_view": true,
            "po_group_index": 0,
            "po_index": 0,
            "custom_group_name": "Default",
            "custom_group_index": 0,
            "custom_index": 1,
            "custom_po_index": 0,
            "is_lock_estimate": false,
            "is_lock_proposal": false,
            "is_press_enter": false,
            "default_value": "",
            "default_dropdown_value": {},
            "default_material_value": {},
            "po_group_name": "this have 2 data entries"
        },
        {
            "id": 168324,
            "value": "",
            "data_entry": {
                "id": 472,
                "name": "entries 1",
                "unit": null,
                "dropdown": [
                    {
                        "id": 1,
                        "name": "abc",
                        "value": "12"
                    }
                ],
                "is_dropdown": true,
                "is_material_selection": false,
                "material_selections": [],
                "created_date": "2024-05-08T02:25:55.792811Z",
                "modified_date": "2024-05-08T02:25:55.792831Z",
                "levels": [],
                "material": {},
                "default_column": {},
                "content_type": 75,
                "catalog": {},
                "category": {}
            },
            "index": null,
            "dropdown_value": {},
            "material_value": {},
            "nick_name": "entries 1",
            "copies_from": [
                {
                    "id": 158537,
                    "formula": 82265,
                    "data_entry": 472,
                    "formula_name": "this use 2 data entries with 1"
                }
            ],
            "group": "",
            "material_data_entry_link": null,
            "levels": [],
            "is_client_view": true,
            "po_group_index": 0,
            "po_index": 0,
            "custom_group_name": "Default",
            "custom_group_index": 0,
            "custom_index": 2,
            "custom_po_index": 0,
            "is_lock_estimate": false,
            "is_lock_proposal": false,
            "is_press_enter": false,
            "default_value": "",
            "default_dropdown_value": {},
            "default_material_value": {},
            "po_group_name": "this use 2 data entries with 1"
        },
        {
            "id": 168325,
            "value": "",
            "data_entry": {
                "id": 250,
                "name": "lolipop",
                "unit": {
                    "id": 54,
                    "name": "test 03"
                },
                "dropdown": [
                    {
                        "name": "",
                        "value": ""
                    }
                ],
                "is_dropdown": false,
                "is_material_selection": false,
                "material_selections": [],
                "created_date": "2024-01-29T02:43:00.174839Z",
                "modified_date": "2024-01-29T02:43:00.174858Z",
                "levels": [],
                "material": {},
                "default_column": {},
                "content_type": 75,
                "catalog": {},
                "category": {}
            },
            "index": null,
            "dropdown_value": {},
            "material_value": {},
            "nick_name": "lolipop",
            "copies_from": [
                {
                    "id": 158538,
                    "formula": 82265,
                    "data_entry": 250,
                    "formula_name": "this use 2 data entries with 1"
                }
            ],
            "group": "",
            "material_data_entry_link": null,
            "levels": [],
            "is_client_view": true,
            "po_group_index": 0,
            "po_index": 0,
            "custom_group_name": "Default",
            "custom_group_index": 0,
            "custom_index": 3,
            "custom_po_index": 0,
            "is_lock_estimate": false,
            "is_lock_proposal": false,
            "is_press_enter": false,
            "default_value": "",
            "default_dropdown_value": {},
            "default_material_value": {},
            "po_group_name": "this use 2 data entries with 1"
        },
        {
            "id": 168326,
            "value": "0.00",
            "data_entry": {
                "id": 323,
                "name": "Quantity with relation00",
                "unit": null,
                "dropdown": [
                    {
                        "id": 1,
                        "name": "custom",
                        "value": "10"
                    }
                ],
                "is_dropdown": true,
                "is_material_selection": false,
                "material_selections": [],
                "created_date": "2024-03-19T23:19:59.951365Z",
                "modified_date": "2024-04-09T09:04:06.050493Z",
                "levels": [],
                "material": {},
                "default_column": {},
                "content_type": 75,
                "catalog": {},
                "category": {}
            },
            "index": null,
            "dropdown_value": {},
            "material_value": {},
            "nick_name": "Quantity with relation00",
            "copies_from": [
                {
                    "id": 158321,
                    "formula": 13443,
                    "data_entry": 323,
                    "formula_name": "update empty data entry 2 (2)"
                }
            ],
            "group": "",
            "material_data_entry_link": null,
            "levels": [],
            "is_client_view": true,
            "po_group_index": 0,
            "po_index": 0,
            "custom_group_name": "Default",
            "custom_group_index": 0,
            "custom_index": 4,
            "custom_po_index": 0,
            "is_lock_estimate": false,
            "is_lock_proposal": false,
            "is_press_enter": false,
            "default_value": "0.00",
            "default_dropdown_value": {},
            "default_material_value": {},
            "po_group_name": "update empty data entry 2 (2)"
        },
        {
            "id": 168327,
            "value": "",
            "data_entry": {
                "id": 472,
                "name": "entries 1",
                "unit": null,
                "dropdown": [
                    {
                        "id": 1,
                        "name": "abc",
                        "value": "12"
                    }
                ],
                "is_dropdown": true,
                "is_material_selection": false,
                "material_selections": [],
                "created_date": "2024-05-08T02:25:55.792811Z",
                "modified_date": "2024-05-08T02:25:55.792831Z",
                "levels": [],
                "material": {},
                "default_column": {},
                "content_type": 75,
                "catalog": {},
                "category": {}
            },
            "index": null,
            "dropdown_value": {
                "id": 1,
                "name": "abc",
                "value": "12"
            },
            "material_value": {},
            "nick_name": "entries 1",
            "copies_from": [
                {
                    "id": 158322,
                    "formula": 13443,
                    "data_entry": 472,
                    "formula_name": "update empty data entry 2 (2)"
                }
            ],
            "group": "",
            "material_data_entry_link": null,
            "levels": [],
            "is_client_view": true,
            "po_group_index": 0,
            "po_index": 0,
            "custom_group_name": "Default",
            "custom_group_index": 0,
            "custom_index": 5,
            "custom_po_index": 0,
            "is_lock_estimate": false,
            "is_lock_proposal": false,
            "is_press_enter": false,
            "default_value": "",
            "default_dropdown_value": {
                "id": 1,
                "name": "abc",
                "value": "12"
            },
            "default_material_value": {},
            "po_group_name": "update empty data entry 2 (2)"
        },
        {
            "id": 168328,
            "value": "",
            "data_entry": {
                "id": 471,
                "name": "entries 2",
                "unit": null,
                "dropdown": [
                    {
                        "id": 1,
                        "name": "drop 1",
                        "value": "2"
                    },
                    {
                        "id": 2,
                        "name": "drop 3",
                        "value": "4"
                    }
                ],
                "is_dropdown": true,
                "is_material_selection": false,
                "material_selections": [],
                "created_date": "2024-05-08T02:24:54.927380Z",
                "modified_date": "2024-05-08T02:24:54.927396Z",
                "levels": [],
                "material": {},
                "default_column": {},
                "content_type": 75,
                "catalog": {},
                "category": {}
            },
            "index": null,
            "dropdown_value": {
                "id": 1,
                "name": "drop 1",
                "value": "2"
            },
            "material_value": {},
            "nick_name": "entries 2",
            "copies_from": [
                {
                    "id": 158323,
                    "formula": 13443,
                    "data_entry": 471,
                    "formula_name": "update empty data entry 2 (2)"
                }
            ],
            "group": "",
            "material_data_entry_link": null,
            "levels": [],
            "is_client_view": true,
            "po_group_index": 0,
            "po_index": 0,
            "custom_group_name": "Default",
            "custom_group_index": 0,
            "custom_index": 6,
            "custom_po_index": 0,
            "is_lock_estimate": false,
            "is_lock_proposal": false,
            "is_press_enter": false,
            "default_value": "",
            "default_dropdown_value": {
                "id": 1,
                "name": "drop 1",
                "value": "2"
            },
            "default_material_value": {},
            "po_group_name": "update empty data entry 2 (2)"
        },
        {
            "id": 168329,
            "value": "15.00",
            "data_entry": {
                "id": 252,
                "name": "Manga Candy",
                "unit": {
                    "id": 56,
                    "name": "Gold2"
                },
                "dropdown": [
                    {
                        "name": "",
                        "value": ""
                    }
                ],
                "is_dropdown": false,
                "is_material_selection": false,
                "material_selections": [],
                "created_date": "2024-01-29T02:56:06.660382Z",
                "modified_date": "2024-01-29T02:56:06.660399Z",
                "levels": [],
                "material": {},
                "default_column": {},
                "content_type": 75,
                "catalog": {},
                "category": {}
            },
            "index": null,
            "dropdown_value": {},
            "material_value": {},
            "nick_name": "Manga Candy",
            "copies_from": [
                {
                    "id": 79289,
                    "formula": 42143,
                    "data_entry": 252,
                    "formula_name": "New for"
                }
            ],
            "group": "",
            "material_data_entry_link": null,
            "levels": [],
            "is_client_view": true,
            "po_group_index": 0,
            "po_index": 0,
            "custom_group_name": "Default",
            "custom_group_index": 0,
            "custom_index": 7,
            "custom_po_index": 0,
            "is_lock_estimate": false,
            "is_lock_proposal": false,
            "is_press_enter": false,
            "default_value": "15.00",
            "default_dropdown_value": {},
            "default_material_value": {},
            "po_group_name": "New for"
        },
        {
            "id": 168330,
            "value": "",
            "data_entry": {
                "id": 469,
                "name": "update data entry 2 2 1",
                "unit": {
                    "id": 325,
                    "name": "cm"
                },
                "dropdown": [
                    {
                        "name": "",
                        "value": ""
                    }
                ],
                "is_dropdown": false,
                "is_material_selection": false,
                "material_selections": [],
                "created_date": "2024-05-08T02:23:29.511197Z",
                "modified_date": "2024-05-08T02:23:29.511223Z",
                "levels": [],
                "material": {},
                "default_column": {},
                "content_type": 75,
                "catalog": {},
                "category": {}
            },
            "index": null,
            "dropdown_value": {
                "id": 2,
                "name": "value 2",
                "value": "2"
            },
            "material_value": {},
            "nick_name": "update data entry 2 2 1",
            "copies_from": [
                {
                    "id": 79290,
                    "formula": 42143,
                    "data_entry": 469,
                    "formula_name": "New for"
                }
            ],
            "group": "",
            "material_data_entry_link": null,
            "levels": [],
            "is_client_view": true,
            "po_group_index": 0,
            "po_index": 0,
            "custom_group_name": "Default",
            "custom_group_index": 0,
            "custom_index": 8,
            "custom_po_index": 0,
            "is_lock_estimate": false,
            "is_lock_proposal": false,
            "is_press_enter": false,
            "default_value": "",
            "default_dropdown_value": {
                "id": 2,
                "name": "value 2",
                "value": "2"
            },
            "default_material_value": {},
            "po_group_name": "New for"
        },
        {
            "id": 168331,
            "value": "",
            "data_entry": {
                "id": 441,
                "name": "update data entry 2 1",
                "unit": null,
                "dropdown": [
                    {
                        "id": 1,
                        "name": "tes",
                        "value": "10"
                    }
                ],
                "is_dropdown": true,
                "is_material_selection": false,
                "material_selections": [],
                "created_date": "2024-04-15T09:34:05.554941Z",
                "modified_date": "2024-04-15T09:34:05.554957Z",
                "levels": [],
                "material": {},
                "default_column": {},
                "content_type": 75,
                "catalog": {},
                "category": {}
            },
            "index": null,
            "dropdown_value": {
                "id": 1,
                "name": "tes",
                "value": "10"
            },
            "material_value": {},
            "nick_name": "update data entry 2 1",
            "copies_from": [
                {
                    "id": 79291,
                    "formula": 40840,
                    "data_entry": 441,
                    "formula_name": "formula. qqq"
                }
            ],
            "group": "",
            "material_data_entry_link": null,
            "levels": [],
            "is_client_view": true,
            "po_group_index": 0,
            "po_index": 0,
            "custom_group_name": "Default",
            "custom_group_index": 0,
            "custom_index": 9,
            "custom_po_index": 0,
            "is_lock_estimate": false,
            "is_lock_proposal": false,
            "is_press_enter": false,
            "default_value": "",
            "default_dropdown_value": {
                "id": 1,
                "name": "tes",
                "value": "10"
            },
            "default_material_value": {},
            "po_group_name": "formula. qqq"
        },
        {
            "id": 168332,
            "value": "2.00",
            "data_entry": {
                "id": 469,
                "name": "update data entry 2 2 1",
                "unit": {
                    "id": 325,
                    "name": "cm"
                },
                "dropdown": [
                    {
                        "name": "",
                        "value": ""
                    }
                ],
                "is_dropdown": false,
                "is_material_selection": false,
                "material_selections": [],
                "created_date": "2024-05-08T02:23:29.511197Z",
                "modified_date": "2024-05-08T02:23:29.511223Z",
                "levels": [],
                "material": {},
                "default_column": {},
                "content_type": 75,
                "catalog": {},
                "category": {}
            },
            "index": null,
            "dropdown_value": {},
            "material_value": {},
            "nick_name": "update data entry 2 2 1",
            "copies_from": [
                {
                    "id": 79292,
                    "formula": 40840,
                    "data_entry": 469,
                    "formula_name": "formula. qqq"
                }
            ],
            "group": "",
            "material_data_entry_link": null,
            "levels": [],
            "is_client_view": true,
            "po_group_index": 0,
            "po_index": 0,
            "custom_group_name": "Default",
            "custom_group_index": 0,
            "custom_index": 10,
            "custom_po_index": 0,
            "is_lock_estimate": false,
            "is_lock_proposal": false,
            "is_press_enter": false,
            "default_value": "2.00",
            "default_dropdown_value": {},
            "default_material_value": {},
            "po_group_name": "formula. qqq"
        },
        {
            "id": 168333,
            "value": "15.00",
            "data_entry": {
                "id": 252,
                "name": "Manga Candy",
                "unit": {
                    "id": 56,
                    "name": "Gold2"
                },
                "dropdown": [
                    {
                        "name": "",
                        "value": ""
                    }
                ],
                "is_dropdown": false,
                "is_material_selection": false,
                "material_selections": [],
                "created_date": "2024-01-29T02:56:06.660382Z",
                "modified_date": "2024-01-29T02:56:06.660399Z",
                "levels": [],
                "material": {},
                "default_column": {},
                "content_type": 75,
                "catalog": {},
                "category": {}
            },
            "index": null,
            "dropdown_value": {},
            "material_value": {},
            "nick_name": "Manga Candy",
            "copies_from": [
                {
                    "id": 79287,
                    "formula": 42139,
                    "data_entry": 252,
                    "formula_name": "New for"
                }
            ],
            "group": "",
            "material_data_entry_link": null,
            "levels": [],
            "is_client_view": true,
            "po_group_index": 0,
            "po_index": 0,
            "custom_group_name": "Default",
            "custom_group_index": 0,
            "custom_index": 11,
            "custom_po_index": 0,
            "is_lock_estimate": false,
            "is_lock_proposal": false,
            "is_press_enter": false,
            "default_value": "15.00",
            "default_dropdown_value": {},
            "default_material_value": {},
            "po_group_name": "New for"
        },
        {
            "id": 168334,
            "value": "",
            "data_entry": {
                "id": 469,
                "name": "update data entry 2 2 1",
                "unit": {
                    "id": 325,
                    "name": "cm"
                },
                "dropdown": [
                    {
                        "name": "",
                        "value": ""
                    }
                ],
                "is_dropdown": false,
                "is_material_selection": false,
                "material_selections": [],
                "created_date": "2024-05-08T02:23:29.511197Z",
                "modified_date": "2024-05-08T02:23:29.511223Z",
                "levels": [],
                "material": {},
                "default_column": {},
                "content_type": 75,
                "catalog": {},
                "category": {}
            },
            "index": null,
            "dropdown_value": {
                "id": 2,
                "name": "value 2",
                "value": "2"
            },
            "material_value": {},
            "nick_name": "update data entry 2 2 1",
            "copies_from": [
                {
                    "id": 79288,
                    "formula": 42139,
                    "data_entry": 469,
                    "formula_name": "New for"
                }
            ],
            "group": "",
            "material_data_entry_link": null,
            "levels": [],
            "is_client_view": true,
            "po_group_index": 0,
            "po_index": 0,
            "custom_group_name": "Default",
            "custom_group_index": 0,
            "custom_index": 12,
            "custom_po_index": 0,
            "is_lock_estimate": false,
            "is_lock_proposal": false,
            "is_press_enter": false,
            "default_value": "",
            "default_dropdown_value": {
                "id": 2,
                "name": "value 2",
                "value": "2"
            },
            "default_material_value": {},
            "po_group_name": "New for"
        },
        {
            "id": 168335,
            "value": "",
            "data_entry": {
                "id": 468,
                "name": "update data entry 2 2",
                "unit": {
                    "id": 325,
                    "name": "cm"
                },
                "dropdown": [
                    {
                        "name": "",
                        "value": ""
                    }
                ],
                "is_dropdown": false,
                "is_material_selection": false,
                "material_selections": [],
                "created_date": "2024-05-08T02:22:57.976983Z",
                "modified_date": "2024-05-08T02:22:57.976999Z",
                "levels": [],
                "material": {},
                "default_column": {},
                "content_type": 75,
                "catalog": {},
                "category": {}
            },
            "index": null,
            "dropdown_value": {
                "id": 2,
                "name": "value 2",
                "value": "2"
            },
            "material_value": {},
            "nick_name": "update data entry 2 2",
            "copies_from": [
                {
                    "id": 79242,
                    "formula": 42143,
                    "data_entry": 468,
                    "formula_name": "New for"
                }
            ],
            "group": "",
            "material_data_entry_link": null,
            "levels": [],
            "is_client_view": true,
            "po_group_index": 0,
            "po_index": 0,
            "custom_group_name": "Default",
            "custom_group_index": 0,
            "custom_index": 13,
            "custom_po_index": 0,
            "is_lock_estimate": false,
            "is_lock_proposal": false,
            "is_press_enter": false,
            "default_value": "",
            "default_dropdown_value": {
                "id": 2,
                "name": "value 2",
                "value": "2"
            },
            "default_material_value": {},
            "po_group_name": "New for"
        },
        {
            "id": 168336,
            "value": "",
            "data_entry": {
                "id": 471,
                "name": "entries 2",
                "unit": null,
                "dropdown": [
                    {
                        "id": 1,
                        "name": "drop 1",
                        "value": "2"
                    },
                    {
                        "id": 2,
                        "name": "drop 3",
                        "value": "4"
                    }
                ],
                "is_dropdown": true,
                "is_material_selection": false,
                "material_selections": [],
                "created_date": "2024-05-08T02:24:54.927380Z",
                "modified_date": "2024-05-08T02:24:54.927396Z",
                "levels": [],
                "material": {},
                "default_column": {},
                "content_type": 75,
                "catalog": {},
                "category": {}
            },
            "index": null,
            "dropdown_value": {
                "id": 1,
                "name": "drop 1",
                "value": "2"
            },
            "material_value": {},
            "nick_name": "entries 2",
            "copies_from": [
                {
                    "id": 160865,
                    "formula": 83163,
                    "data_entry": 471,
                    "formula_name": "this have 2 data entries"
                }
            ],
            "group": "",
            "material_data_entry_link": null,
            "levels": [],
            "is_client_view": true,
            "po_group_index": 0,
            "po_index": 0,
            "custom_group_name": "New Group",
            "custom_group_index": 1,
            "custom_index": 2,
            "custom_po_index": 0,
            "is_lock_estimate": false,
            "is_lock_proposal": false,
            "is_press_enter": false,
            "default_value": "",
            "default_dropdown_value": {
                "id": 1,
                "name": "drop 1",
                "value": "2"
            },
            "default_material_value": {},
            "po_group_name": "this have 2 data entries"
        },
        {
            "id": 168337,
            "value": "",
            "data_entry": {
                "id": 409,
                "name": "Quantity",
                "unit": {
                    "id": 230,
                    "name": "Ton"
                },
                "dropdown": [
                    {
                        "name": "",
                        "value": ""
                    }
                ],
                "is_dropdown": false,
                "is_material_selection": false,
                "material_selections": [],
                "created_date": "2024-04-09T04:54:59.454851Z",
                "modified_date": "2024-04-09T04:54:59.454867Z",
                "levels": [],
                "material": {},
                "default_column": {},
                "content_type": 75,
                "catalog": {},
                "category": {}
            },
            "index": null,
            "dropdown_value": {},
            "material_value": {},
            "nick_name": "Quantity",
            "copies_from": [
                {
                    "id": 160866,
                    "formula": 83163,
                    "data_entry": 409,
                    "formula_name": "this have 2 data entries"
                }
            ],
            "group": "",
            "material_data_entry_link": null,
            "levels": [],
            "is_client_view": true,
            "po_group_index": 0,
            "po_index": 0,
            "custom_group_name": "New Group",
            "custom_group_index": 1,
            "custom_index": 3,
            "custom_po_index": 0,
            "is_lock_estimate": false,
            "is_lock_proposal": false,
            "is_press_enter": false,
            "default_value": "",
            "default_dropdown_value": {},
            "default_material_value": {},
            "po_group_name": "this have 2 data entries"
        },
        {
            "id": 168338,
            "value": "",
            "data_entry": {
                "id": 382,
                "name": "new unit type",
                "unit": {
                    "id": 311,
                    "name": "new unit type"
                },
                "dropdown": [
                    {
                        "name": "",
                        "value": ""
                    }
                ],
                "is_dropdown": false,
                "is_material_selection": false,
                "material_selections": [],
                "created_date": "2024-04-02T08:27:04.477884Z",
                "modified_date": "2024-04-02T08:27:04.477903Z",
                "levels": [],
                "material": {},
                "default_column": {},
                "content_type": 75,
                "catalog": {},
                "category": {}
            },
            "index": null,
            "dropdown_value": {},
            "material_value": {},
            "nick_name": "new unit type",
            "copies_from": [
                {
                    "id": 160867,
                    "formula": 83163,
                    "data_entry": 382,
                    "formula_name": "this have 2 data entries"
                }
            ],
            "group": "",
            "material_data_entry_link": null,
            "levels": [],
            "is_client_view": true,
            "po_group_index": 0,
            "po_index": 0,
            "custom_group_name": "New Group",
            "custom_group_index": 1,
            "custom_index": 4,
            "custom_po_index": 0,
            "is_lock_estimate": false,
            "is_lock_proposal": false,
            "is_press_enter": false,
            "default_value": "",
            "default_dropdown_value": {},
            "default_material_value": {},
            "po_group_name": "this have 2 data entries"
        }
    ],
    "material_views": [
        {
            "id": 11180,
            "name": "update empty data entry 2 (2)",
            "material_value": {
                "id": "771:0",
                "bud": "2 + @[material 1 -cost](771material 1 cost) ",
                "cost": "100",
                "name": "material 1 ",
                "unit": "Gold2",
                "Cost 2": "1",
                "levels": [
                    {
                        "id": 192,
                        "name": "Nana Coffee's",
                        "level": null,
                        "level_index": 0
                    },
                    {
                        "id": 193,
                        "name": "Drinks",
                        "level": null,
                        "level_index": 0
                    },
                    {
                        "id": 195,
                        "name": "Carrot Juice",
                        "level": 75,
                        "level_index": 0
                    },
                    {
                        "id": 771,
                        "name": "abc",
                        "level": 76,
                        "level_index": 1
                    }
                ],
                "columns": [
                    {
                        "name": "name",
                        "value": "material 1 "
                    },
                    {
                        "name": "unit",
                        "value": "Gold2"
                    },
                    {
                        "name": "cost",
                        "value": "100"
                    },
                    {
                        "name": "Cost 2",
                        "value": "1"
                    },
                    {
                        "name": "bud",
                        "value": "2 + @[material 1 -cost](771material 1 cost) "
                    }
                ]
            },
            "copies_from": [
                {
                    "formula": 13443
                },
                {
                    "formula": 13443
                }
            ],
            "catalog_materials": [
                {
                    "id": 192,
                    "name": "Nana Coffee's",
                    "data_points": []
                },
                {
                    "id": 193,
                    "name": "Drinks",
                    "data_points": []
                },
                {
                    "id": 195,
                    "name": "Carrot Juice",
                    "data_points": [
                        {
                            "id": 5442,
                            "name": "Carrot Juice",
                            "linked_description": ""
                        },
                        {
                            "id": 417,
                            "name": "Carrot Juice",
                            "linked_description": ""
                        }
                    ]
                },
                {
                    "id": 771,
                    "name": "abc",
                    "data_points": [
                        {
                            "id": 5444,
                            "name": "abc",
                            "linked_description": ""
                        }
                    ]
                }
            ],
            "levels": [
                {
                    "id": 192,
                    "name": "Nana Coffee's",
                    "data_points": []
                },
                {
                    "id": 193,
                    "name": "Drinks",
                    "data_points": []
                },
                {
                    "id": 195,
                    "name": "Carrot Juice",
                    "data_points": [
                        {
                            "id": 5442,
                            "name": "Carrot Juice",
                            "linked_description": ""
                        },
                        {
                            "id": 417,
                            "name": "Carrot Juice",
                            "linked_description": ""
                        }
                    ]
                },
                {
                    "id": 771,
                    "name": "abc",
                    "data_points": [
                        {
                            "id": 5444,
                            "name": "abc",
                            "linked_description": ""
                        }
                    ]
                }
            ],
            "data_entry": null,
            "is_client_view": false,
            "default_column": {
                "name": "cost",
                "value": "100"
            },
            "custom_po_index": 0,
            "po_group_index": 0,
            "po_index": 0,
            "custom_group_name": "Default",
            "custom_group_index": 0,
            "custom_index": 15,
            "is_lock_estimate": false,
            "is_lock_proposal": null,
            "is_press_enter": false,
            "default_value": "",
            "default_material_value": {
                "id": "771:0",
                "bud": "2 + @[material 1 -cost](771material 1 cost) ",
                "cost": "100",
                "name": "material 1 ",
                "unit": "Gold2",
                "Cost 2": "1",
                "levels": [
                    {
                        "id": 192,
                        "name": "Nana Coffee's",
                        "level": null,
                        "level_index": 0
                    },
                    {
                        "id": 193,
                        "name": "Drinks",
                        "level": null,
                        "level_index": 0
                    },
                    {
                        "id": 195,
                        "name": "Carrot Juice",
                        "level": 75,
                        "level_index": 0
                    },
                    {
                        "id": 771,
                        "name": "abc",
                        "level": 76,
                        "level_index": 1
                    }
                ],
                "columns": [
                    {
                        "name": "name",
                        "value": "material 1 "
                    },
                    {
                        "name": "unit",
                        "value": "Gold2"
                    },
                    {
                        "name": "cost",
                        "value": "100"
                    },
                    {
                        "name": "Cost 2",
                        "value": "1"
                    },
                    {
                        "name": "bud",
                        "value": "2 + @[material 1 -cost](771material 1 cost) "
                    }
                ]
            },
            "default_dropdown_value": {},
            "po_group_name": "update empty data entry 2 (2)"
        },
        {
            "id": 11181,
            "name": "For 2 1",
            "material_value": {
                "id": "50897:0",
                "cost": "20",
                "name": "UPS - all size",
                "unit": "kg",
                "levels": [
                    {
                        "id": 50887,
                        "name": "cong catalog",
                        "level": null,
                        "level_index": 0
                    },
                    {
                        "id": 50896,
                        "name": "Shiping Cost",
                        "level": null,
                        "level_index": 0
                    },
                    {
                        "id": 50897,
                        "name": "Singapore",
                        "level": 1692,
                        "level_index": 0
                    }
                ],
                "columns": [
                    {
                        "name": "name",
                        "value": "UPS - all size"
                    },
                    {
                        "name": "unit",
                        "value": "kg"
                    },
                    {
                        "name": "cost",
                        "value": "20"
                    }
                ]
            },
            "copies_from": [
                {
                    "formula": 83176
                }
            ],
            "catalog_materials": [
                {
                    "id": 50887,
                    "name": "cong catalog",
                    "data_points": []
                },
                {
                    "id": 50896,
                    "name": "Shiping Cost",
                    "data_points": []
                },
                {
                    "id": 50897,
                    "name": "Singapore",
                    "data_points": [
                        {
                            "id": 78953,
                            "name": "Singapore",
                            "linked_description": "aaaa"
                        }
                    ]
                }
            ],
            "levels": [
                {
                    "id": 50887,
                    "name": "cong catalog",
                    "data_points": []
                },
                {
                    "id": 50896,
                    "name": "Shiping Cost",
                    "data_points": []
                },
                {
                    "id": 50897,
                    "name": "Singapore",
                    "data_points": [
                        {
                            "id": 78953,
                            "name": "Singapore",
                            "linked_description": "aaaa"
                        }
                    ]
                }
            ],
            "data_entry": null,
            "is_client_view": false,
            "default_column": {
                "name": "name",
                "value": "UPS - all size"
            },
            "custom_po_index": 0,
            "po_group_index": 0,
            "po_index": 0,
            "custom_group_name": "Default",
            "custom_group_index": 0,
            "custom_index": 16,
            "is_lock_estimate": false,
            "is_lock_proposal": null,
            "is_press_enter": false,
            "default_value": "",
            "default_material_value": {
                "id": "50897:0",
                "cost": "20",
                "name": "UPS - all size",
                "unit": "kg",
                "levels": [
                    {
                        "id": 50887,
                        "name": "cong catalog",
                        "level": null,
                        "level_index": 0
                    },
                    {
                        "id": 50896,
                        "name": "Shiping Cost",
                        "level": null,
                        "level_index": 0
                    },
                    {
                        "id": 50897,
                        "name": "Singapore",
                        "level": 1692,
                        "level_index": 0
                    }
                ],
                "columns": [
                    {
                        "name": "name",
                        "value": "UPS - all size"
                    },
                    {
                        "name": "unit",
                        "value": "kg"
                    },
                    {
                        "name": "cost",
                        "value": "20"
                    }
                ]
            },
            "default_dropdown_value": {},
            "po_group_name": "For 2 1"
        }
    ],
    "quantity": {
        "id": -1,
        "name": "Total Cost",
        "type": "data_view"
    },
    "unit": {
        "id": 368,
        "name": "0"
    },
    "created_date": "2024-05-20T03:40:53.412532Z",
    "modified_date": "2024-05-31T07:25:19.636342Z",
    "name": "testing for Scott",
    "proposal_name": "",
    "contract_description": "",
    "catalog_links": [],
    "is_show": true,
    "original": 24415,
    "order": 0,
    "format_order": 0,
    "is_selected": false,
    "is_checked": false,
    "description": "",
    "changed_description": "",
    "note": "",
    "changed_items": [],
    "tab": 0,
    "is_custom_estimate": false,
    "user_create": 18,
    "user_update": 5,
    "company": 1,
    "group_by_proposal": null,
    "content_type": 83
}