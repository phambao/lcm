from django.contrib.contenttypes.models import ContentType
from django.db import IntegrityError
from django.db.models import Sum, DecimalField
from django.db.models.functions import Cast
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from base.serializers.base import IDAndNameSerializer
from base.constants import true, null, false
from base.tasks import activity_log
from base.utils import pop, extra_kwargs_for_base_model
from sales.apps import PO_FORMULA_CONTENT_TYPE, DESCRIPTION_LIBRARY_CONTENT_TYPE, \
    UNIT_LIBRARY_CONTENT_TYPE, DATA_ENTRY_CONTENT_TYPE, ESTIMATE_TEMPLATE_CONTENT_TYPE, ASSEMBLE_CONTENT_TYPE
from sales.models import DataPoint, Catalog
from sales.models.estimate import POFormula, POFormulaGrouping, DataEntry, POFormulaToDataEntry, \
    UnitLibrary, DescriptionLibrary, Assemble, EstimateTemplate, DataView, MaterialView
from sales.serializers.catalog import CatalogEstimateSerializer


class SerializerMixin:
    def is_in_proposal_view(self):
        if self.context.get('view'):
            from sales.views import proposal
            from sales.views import change_order
            views = [proposal.PriceComparisonList, proposal.PriceComparisonDetail,
                     proposal.ProposalWritingList, proposal.ProposalWritingDetail,
                     change_order.ChangeOderDetail, change_order.ChangeOderList]
            return any([isinstance(self.context['view'], view) for view in views])

    def is_in_proposal_writing_view(self):
        if self.context.get('view'):
            from sales.views import proposal
            views = [proposal.ProposalWritingList, proposal.ProposalWritingDetail]
            return any([isinstance(self.context['view'], view) for view in views])


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


class DataEntrySerializer(serializers.ModelSerializer):
    unit = IDAndNameSerializer(required=False, allow_null=True)
    material_selections = CatalogEstimateSerializer('data_entries', many=True, required=False, allow_null=True)

    class Meta:
        model = DataEntry
        fields = ('id', 'name', 'unit', 'dropdown', 'is_dropdown', 'is_material_selection', 'material_selections',
                  'created_date', 'modified_date')
        extra_kwargs = {'id': {'read_only': False, 'required': False}}
        read_only_fields = ('created_date', 'modified_date')

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
            activity_log.delay(DATA_ENTRY_CONTENT_TYPE, instance.pk, 1,
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

        activity_log.delay(DATA_ENTRY_CONTENT_TYPE, instance.pk, 2,
                           DataEntrySerializer.__name__, __name__, self.context['request'].user.pk)
        return update

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['content_type'] = DATA_ENTRY_CONTENT_TYPE
        data['catalog'] = {}
        data['category'] = {}
        if data['material_selections']:
            parent = Catalog.objects.get(pk=data['material_selections'][0].get('id'))
            parent = parent.parents.first()
            data['category'] = CatalogEstimateSerializer(parent).data
            parent = parent.parents.first()
            data['catalog'] = CatalogEstimateSerializer(parent).data
        return data


class POFormulaToDataEntrySerializer(serializers.ModelSerializer):
    data_entry = DataEntrySerializer(allow_null=True, required=False)

    class Meta:
        model = POFormulaToDataEntry
        fields = ('id', 'value', 'data_entry', 'index', 'dropdown_value', 'material_value',
                  'copies_from', 'group', 'material_data_entry_link')

    def to_representation(self, instance):
        data = super(POFormulaToDataEntrySerializer, self).to_representation(instance)
        return data


def create_po_formula_to_data_entry(instance, data_entries, estimate_id=None):
    data = []
    for data_entry in data_entries:
        params = {"po_formula_id": instance.pk, "value": data_entry['value'], 'index': data_entry.get('index'),
                  'dropdown_value': data_entry.get('dropdown_value', ''), 'estimate_template_id': estimate_id,
                  'material_value': data_entry.get('material_value', ''), 'copies_from': data_entry.get('copies_from'),
                  'group': data_entry.get('group', ''), 'material_data_entry_link': data_entry.get('material_data_entry_link')}
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
        fields = ('id', 'name', 'total_cost')

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


class POFormulaCompactSerializer(serializers.ModelSerializer, SerializerMixin):

    class Meta:
        model = POFormula
        exclude = ('material', 'formula_mentions', 'formula_data_mentions', 'description_of_formula', 'assemble', 'order',
                   'formula_scenario', 'formula_for_data_view', 'original', 'catalog_materials', 'company', 'created_from')


class POFormulaSerializer(serializers.ModelSerializer, SerializerMixin):
    self_data_entries = POFormulaToDataEntrySerializer('po_formula', many=True, required=False, read_only=False)

    class Meta:
        model = POFormula
        fields = '__all__'
        extra_kwargs = {**{'id': {'read_only': False, 'required': False}}, **extra_kwargs_for_base_model()}

    def reparse(self, data):
        # Serializer is auto convert pk to model, But when reuse serializer in others, it is required to have int field.
        # So we reparse this case
        assemble = data.get('assemble')
        if isinstance(assemble, int):
            data['assemble'] = Assemble.objects.get(pk=assemble)
        group = data.get('group')
        if isinstance(group, int):
            data['group'] = POFormulaGrouping.objects.get(pk=group)
        return data

    def create(self, validated_data):
        data_entries = pop(validated_data, 'self_data_entries', [])
        validated_data = self.reparse(validated_data)
        pop(validated_data, 'id', None)
        instance = super().create(validated_data)
        create_po_formula_to_data_entry(instance, data_entries)

        from sales.views.estimate import POFormulaList
        if isinstance(self.context.get('view'), POFormulaList):
            activity_log.delay(PO_FORMULA_CONTENT_TYPE, instance.pk, 1,
                               POFormulaSerializer.__name__, __name__, self.context['request'].user.pk)
        return instance

    def update(self, instance, validated_data):
        data_entries = pop(validated_data, 'self_data_entries', [])
        instance.self_data_entries.all().delete()
        create_po_formula_to_data_entry(instance, data_entries)
        activity_log.delay(PO_FORMULA_CONTENT_TYPE, instance.pk, 2,
                           POFormulaSerializer.__name__, __name__, self.context['request'].user.pk)
        validated_data = self.reparse(validated_data)
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

    def to_internal_value(self, data):
        data = super().to_internal_value(data)
        if self.is_in_proposal_view():
            assemble = data.get('assemble')
            if isinstance(assemble, Assemble):
                data['assemble'] = assemble.pk
            group = data.get('group')
            if isinstance(group, POFormulaGrouping):
                data['group'] = group.pk
        return data

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
        linked_descriptions = []
        try:
            linked_descriptions = eval(data['linked_description'])
        except:
            pass
        data['linked_description'] = []
        for linked_description in linked_descriptions:
            if isinstance(linked_description, dict):
                linked_description = linked_description.get('id', '')
                if not isinstance(linked_description, str):
                    continue
                if 'catalog' in linked_description or 'estimate' in linked_description:
                    pk = linked_description.split(':')[1]
                    if 'estimate' in linked_description:
                        try:
                            linked_description = DescriptionLibrary.objects.get(pk=pk)
                        except DescriptionLibrary.DoesNotExist:
                            continue
                    else:
                        try:
                            linked_description = DataPoint.objects.get(pk=pk)
                        except DataPoint.DoesNotExist:
                            continue
                    data['linked_description'].append(LinkedDescriptionSerializer(linked_description).data)
        data['linked_description'] = str(data['linked_description'])

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
        else:
            data['catalog_materials'] = [i for i in data['catalog_materials'] if i]
            data['material_value'] = {}
            data['catalog_ancestor'] = None
            data['catalog_link'] = []

        data['content_type'] = PO_FORMULA_CONTENT_TYPE
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
                po_formula['group'] = instance.pk
                po_formula['is_show'] = True
                po = POFormulaSerializer(data=po_formula)
                po.is_valid(raise_exception=True)
                po.save()
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


class UnitLibrarySerializer(serializers.ModelSerializer):
    class Meta:
        model = UnitLibrary
        fields = ('id', 'name', 'description', 'created_date', 'modified_date', 'user_create', 'user_update')

    def create(self, validated_data):
        try:
            instance = super().create(validated_data)
        except IntegrityError:
            raise serializers.ValidationError({'name': 'name is duplicated'})

        from sales.views.estimate import UnitLibraryList
        if isinstance(self.context.get('view'), UnitLibraryList):
            activity_log.delay(UNIT_LIBRARY_CONTENT_TYPE, instance.pk, 1,
                               UnitLibrarySerializer.__name__, __name__, self.context['request'].user.pk)
        return instance

    def update(self, instance, validated_data):
        try:
            obj = super().update(instance, validated_data)
        except IntegrityError:
            raise serializers.ValidationError({'name': 'name is duplicated'})
        activity_log.delay(UNIT_LIBRARY_CONTENT_TYPE, instance.pk, 2,
                           UnitLibrarySerializer.__name__, __name__, self.context['request'].user.pk)
        return obj

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['content_type'] = UNIT_LIBRARY_CONTENT_TYPE
        return data


class DescriptionLibrarySerializer(serializers.ModelSerializer):
    class Meta:
        model = DescriptionLibrary
        fields = ('id', 'name', 'linked_description', 'created_date', 'modified_date')
        read_only_fields = ('created_date', 'modified_date')

    def create(self, validated_data):
        instance = super().create(validated_data)

        from sales.views.estimate import DescriptionLibraryList
        if isinstance(self.context.get('view'), DescriptionLibraryList):
            activity_log.delay(DESCRIPTION_LIBRARY_CONTENT_TYPE, instance.pk, 1,
                               DescriptionLibrarySerializer.__name__, __name__, self.context['request'].user.pk)
        return instance

    def update(self, instance, validated_data):
        activity_log.delay(DESCRIPTION_LIBRARY_CONTENT_TYPE, instance.pk, 2,
                           DescriptionLibrarySerializer.__name__, __name__, self.context['request'].user.pk)
        return super().update(instance, validated_data)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['content_type'] = DESCRIPTION_LIBRARY_CONTENT_TYPE
        return data


class AssembleCompactSerializer(serializers.ModelSerializer):

    class Meta:
        model = Assemble
        fields = ('id', 'name', 'created_date', 'modified_date', 'user_create', 'user_update', 'description')

    def create(self, validated_data):
        raise ValidationError('Can not Create')


class AssembleSerializer(serializers.ModelSerializer):
    assemble_formulas = POFormulaSerializer('assemble', many=True, required=False, allow_null=True)

    class Meta:
        model = Assemble
        fields = ('id', 'name', 'created_date', 'modified_date', 'user_create', 'user_update',
                  'assemble_formulas', 'description', 'is_show', 'original')
        extra_kwargs = extra_kwargs_for_base_model()

    def create_po_formula(self, po_formulas, instance):
        for po_formula in po_formulas:
            po_formula['assemble'] = instance.pk
            po_formula['is_show'] = False
            created_from = po_formula.get('created_from')
            if not created_from:
                po_formula['created_from'] = po_formula['id']
            from sales.views.estimate import EstimateTemplateList
            if self.context.get('request').method == 'POST' and isinstance(self.context.get('view'), EstimateTemplateList):
                po_formula['formula_for_data_view'] = po_formula.get('id')
            del po_formula['group']
            del po_formula['id']
            po = POFormulaSerializer(data=po_formula, context=self.context)
            po.is_valid(raise_exception=True)
            po.save()

    def create(self, validated_data):
        po_formulas = pop(validated_data, 'assemble_formulas', [])
        instance = super().create(validated_data)
        self.create_po_formula(po_formulas, instance)

        from sales.views.estimate import AssembleList
        if isinstance(self.context.get('view'), AssembleList):
            activity_log.delay(ASSEMBLE_CONTENT_TYPE, instance.pk, 1,
                               AssembleSerializer.__name__, __name__, self.context['request'].user.pk)
        return instance

    def update(self, instance, validated_data):
        po_formulas = pop(validated_data, 'assemble_formulas', [])
        instance.assemble_formulas.all().delete()
        self.create_po_formula(po_formulas, instance)
        activity_log.delay(ASSEMBLE_CONTENT_TYPE, instance.pk, 2,
                           AssembleSerializer.__name__, __name__, self.context['request'].user.pk)
        return super().update(instance, validated_data)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['content_type'] = ASSEMBLE_CONTENT_TYPE
        original = data.get('original')
        if not original:
            data['original'] = instance.pk
        return data


class DataViewSerializer(serializers.ModelSerializer, SerializerMixin):
    class Meta:
        model = DataView
        fields = ('id', 'formula', 'name', 'estimate_template', 'type')

    def to_internal_value(self, data):
        data = super().to_internal_value(data)
        if self.is_in_proposal_view():
            estimate_template = data['estimate_template']
            if isinstance(estimate_template, EstimateTemplate):
                data['estimate_template'] = estimate_template.pk
        return data


class MaterialViewSerializers(serializers.ModelSerializer):
    data_entry = serializers.IntegerField(allow_null=True, required=False)
    class Meta:
        model = MaterialView
        fields = ('id', 'name', 'material_value', 'copies_from', 'catalog_materials',
                  'material_data_entry_link', 'data_entry')

    def validate_data_entry(self, value):
        if value:
            try:
                DataEntry.objects.get(pk=value)
            except DataEntry.DoesNotExist:
                raise serializers.ValidationError('Data Entry is not exist')
        return value


class EstimateTemplateForFormattingSerializer(serializers.ModelSerializer):

    class Meta:
        model = EstimateTemplate
        fields = ('id', 'name', 'quantity', 'unit')

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['quantity'] = ''
        data['unit'] = ''
        if instance.unit:
            try:
                data['unit'] = UnitLibrary.objects.get(pk=instance.unit).name
            except (UnitLibrary.DoesNotExist, ValueError):
                pass
        if instance.quantity:
            try:
                data['quantity'] = DataEntry.objects.get(pk=instance.quantity).name
            except (DataEntry.DoesNotExist):
                pass
        data['total_charge'] = instance.get_formula().aggregate(
            total_charge=Sum('charge')
        ).get('total_charge')
        return data


class EstimateTemplateCompactSerializer(serializers.ModelSerializer, SerializerMixin):

    class Meta:
        model = EstimateTemplate
        exclude = ('is_show', 'original', 'order', 'assembles', 'group_by_proposal', 'company', 'is_checked')


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


class EstimateTemplateSerializer(serializers.ModelSerializer, SerializerMixin):
    assembles = AssembleSerializer(many=True, required=False, allow_null=True,)
    data_views = DataViewSerializer('estimate_template', many=True, required=False, allow_null=True)
    data_entries = POFormulaToDataEntrySerializer('estimate_template', many=True, required=False, allow_null=True)
    material_views = MaterialViewSerializers('estimate_template', many=True, required=False, allow_null=True)

    class Meta:
        model = EstimateTemplate
        fields = '__all__'
        extra_kwargs = {**{'id': {'read_only': False, 'required': False}}, **extra_kwargs_for_base_model()}

    def reparse(self, data):
        # Serializer is auto convert pk to model, But when reuse serializer in others, it is required to have int field.
        # So we reparse this case
        from sales.models import GroupByEstimate
        group_by_proposal = data.get('group_by_proposal')
        if isinstance(group_by_proposal, int):
            data['group_by_proposal'] = GroupByEstimate.objects.get(pk=group_by_proposal)
        return data

    def create_assembles(self, assembles):
        pk_assembles = []
        for assemble in assembles:
            for po in assemble.get('assemble_formulas', []):
                ### Need to clean this up
                if po.get('assemble'):
                    if isinstance(po['assemble'], Assemble):
                        po['assemble'] = po['assemble'].pk
                if po.get('group'):
                    if isinstance(po['group'], POFormulaGrouping):
                        po['group'] = po['group'].pk
            serializer = AssembleSerializer(data=assemble, context=self.context)
            serializer.is_valid(raise_exception=True)
            obj = serializer.save(is_show=False)
            pk_assembles.append(obj.pk)
        return pk_assembles

    def create_data_view(self, data_views, instance):
        for data_view in data_views:
            data_view['estimate_template'] = instance.pk
            serializer = DataViewSerializer(data=data_view)
            serializer.is_valid(raise_exception=True)
            serializer.save(estimate_template_id=instance.pk)

    def create_material_view(self, material_views, instance):
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
            serializer.save(estimate_template_id=instance.pk, data_entry=data_entry)

    def create(self, validated_data):
        assembles = pop(validated_data, 'assembles', [])
        data_views = pop(validated_data, 'data_views', [])
        data_entries = pop(validated_data, 'data_entries', [])
        material_views = pop(validated_data, 'material_views', [])
        pk = pop(validated_data, 'id', None)

        pk_assembles = self.create_assembles(assembles)
        validated_data = self.reparse(validated_data)
        instance = super().create(validated_data)
        create_po_formula_to_data_entry(EstimateTemplate(name='name'), data_entries, instance.pk)
        self.create_data_view(data_views, instance)
        self.create_material_view(material_views, instance)
        instance.assembles.add(*Assemble.objects.filter(pk__in=pk_assembles))

        from sales.views.estimate import EstimateTemplateList
        if isinstance(self.context.get('view'), EstimateTemplateList):
            activity_log.delay(ESTIMATE_TEMPLATE_CONTENT_TYPE, instance.pk, 1,
                               EstimateTemplateSerializer.__name__, __name__, self.context['request'].user.pk)
        return instance

    def update(self, instance, validated_data):
        assembles = pop(validated_data, 'assembles', [])
        data_views = pop(validated_data, 'data_views', [])
        data_entries = pop(validated_data, 'data_entries', [])
        material_views = pop(validated_data, 'material_views', [])
        pk = pop(validated_data, 'id', None)

        instance.data_entries.all().delete()
        create_po_formula_to_data_entry(EstimateTemplate(name='name'), data_entries, instance.pk)
        pk_assembles = self.create_assembles(assembles)

        validated_data = self.reparse(validated_data)
        instance = super().update(instance, validated_data)
        instance.data_views.all().delete()
        self.create_data_view(data_views, instance)
        instance.material_views.all().delete()
        self.create_material_view(material_views, instance)

        instance.assembles.all().delete()
        instance.assembles.add(*Assemble.objects.filter(pk__in=pk_assembles))
        activity_log.delay(ESTIMATE_TEMPLATE_CONTENT_TYPE, instance.pk, 2,
                           EstimateTemplateSerializer.__name__, __name__, self.context['request'].user.pk)
        return instance

    def validate_quantity(self, value):
        if value:
            if not DataEntry.objects.filter(pk=value).exists():
                raise serializers.ValidationError('DataEntry does not exsit')
        return value

    def validate_unit(self, value):
        if value:
            if not UnitLibrary.objects.filter(pk=value).exists():
                raise serializers.ValidationError('Unit does not exsit')
        return value

    def to_internal_value(self, data):
        data = super().to_internal_value(data)
        if self.is_in_proposal_view():
            from sales.models import proposal
            group_by_proposal = data.get('group_by_proposal')
            if isinstance(group_by_proposal, proposal.GroupByEstimate):
                data['group_by_proposal'] = group_by_proposal.pk
        return data

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['content_type'] = ESTIMATE_TEMPLATE_CONTENT_TYPE
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
