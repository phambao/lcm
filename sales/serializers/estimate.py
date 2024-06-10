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
from sales.models.estimate import Note, POFormula, POFormulaGrouping, DataEntry, POFormulaToDataEntry, RoundUpActionChoice, RoundUpChoice, \
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


class NoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Note
        fields = ('id', 'description', 'created_date', 'modified_date', 'user_create', 'user_update')
        read_only_fields = ('created_date', 'modified_date', 'user_create', 'user_update')


class POFormulaToDataEntrySerializer(serializers.ModelSerializer):
    data_entry = DataEntrySerializer(allow_null=True, required=False)
    notes = NoteSerializer(many=True, required=False, allow_null=True)

    class Meta:
        model = POFormulaToDataEntry
        fields = ('id', 'value', 'data_entry', 'index', 'dropdown_value', 'material_value', 'nick_name',
                  'copies_from', 'group', 'material_data_entry_link', 'levels', 'is_client_view', 
                  'po_group_index', 'po_index', 'custom_group_name', 'custom_group_index', 'custom_index',
                  'custom_po_index', 'is_lock_estimate', 'is_lock_proposal', 'is_press_enter', 'notes',
                  'default_value', 'default_dropdown_value', 'default_material_value', 'original')

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if not data['nick_name']:
            data['nick_name'] = instance.data_entry.name
        data['po_group_name'] = instance.get_po_group_name()
        if not data['original']:
            data['original'] = instance.pk
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
                  'default_material_value': data_entry.get('default_material_value') or {}, 'original': data_entry.get('original') or 0}
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
            obj = POFormulaToDataEntry.objects.create(**params)
            if data_entry.get('notes'):
                for note in data_entry.get('notes'):
                    Note.objects.create(**note, data_entry=obj)
        except KeyError:
            pass
    # POFormulaToDataEntry.objects.bulk_create(data)


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
        fields = ('id', 'formula', 'name', 'estimate_template', 'type', 'is_client_view', 'unit', 'result', 'original')
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

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if not data['original']:
            data['original'] = data['id']
        return data


class MaterialViewSerializers(serializers.ModelSerializer):
    data_entry = serializers.IntegerField(allow_null=True, required=False)
    class Meta:
        model = MaterialView
        fields = ('id', 'name', 'material_value', 'copies_from', 'catalog_materials',
                  'levels', 'data_entry', 'is_client_view', 'default_column', 'custom_po_index',
                  'po_group_index', 'po_index', 'custom_group_name', 'custom_group_index', 'custom_index',
                  'is_lock_estimate', 'is_lock_proposal', 'is_press_enter', 'default_value', 'default_material_value',
                  'default_dropdown_value', 'original')

    def validate_data_entry(self, value):
        if value:
            try:
                DataEntry.objects.get(pk=value)
            except DataEntry.DoesNotExist:
                return None
        return value

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if isinstance(instance, MaterialView):
            data['po_group_name'] = instance.get_po_group_name()
        if not data['original']:
            data['original'] = instance.pk
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
                params['default_material_value'] = data_view
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
