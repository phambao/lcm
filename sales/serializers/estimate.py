from django.contrib.contenttypes.models import ContentType
from rest_framework import serializers

from base.serializers.base import IDAndNameSerializer
from base.constants import true, null, false
from base.utils import pop, activity_log, extra_kwargs_for_base_model
from sales.apps import PO_FORMULA_CONTENT_TYPE, DESCRIPTION_LIBRARY_CONTENT_TYPE, \
    UNIT_LIBRARY_CONTENT_TYPE, DATA_ENTRY_CONTENT_TYPE, ESTIMATE_TEMPLATE_CONTENT_TYPE, ASSEMBLE_CONTENT_TYPE
from sales.models import DataPoint, Catalog, PriceComparison, ProposalWriting
from sales.models.estimate import POFormula, POFormulaGrouping, DataEntry, POFormulaToDataEntry, \
    UnitLibrary, DescriptionLibrary, Assemble, EstimateTemplate, DataView
from sales.serializers.catalog import CatalogSerializer, CatalogEstimateSerializer


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
        fields = ('id', 'name', 'unit', 'dropdown', 'is_dropdown', 'is_material_selection', 'material_selections')
        extra_kwargs = {'id': {'read_only': False, 'required': False}}

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

        activity_log(DataEntry, instance, 1, DataEntrySerializer, {})
        return instance

    def update(self, instance, validated_data):
        unit = pop(validated_data, 'unit', {})
        material_selections = pop(validated_data, 'material_selections', {})

        instance.material_selections.clear()
        catalogs = self.set_material(material_selections)
        instance.material_selections.add(*catalogs)

        validated_data['unit_id'] = unit.get('id', None)
        activity_log(DataEntry, instance, 2, DataEntrySerializer, {})
        return super().update(instance, validated_data)

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
        fields = ('id', 'value', 'data_entry', 'index', 'dropdown_value', 'material_value', 'copies_from')

    def to_representation(self, instance):
        data = super(POFormulaToDataEntrySerializer, self).to_representation(instance)
        return data


def create_po_formula_to_data_entry(instance, data_entries, estimate_id=None):
    data = []
    for data_entry in data_entries:
        params = {"po_formula_id": instance.pk, "value": data_entry['value'], 'index': data_entry.get('index'),
                  'dropdown_value': data_entry.get('dropdown_value', ''), 'estimate_template_id': estimate_id,
                  'material_value': data_entry.get('material_value', ''), 'copies_from': data_entry.get('copies_from')}
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


class POFormulaSerializer(serializers.ModelSerializer):
    self_data_entries = POFormulaToDataEntrySerializer('po_formula', many=True, required=False, read_only=False)

    class Meta:
        model = POFormula
        fields = '__all__'
        extra_kwargs = {**{'id': {'read_only': False, 'required': False}}, **extra_kwargs_for_base_model()}

    def reparse(self, data):
        # Serializer is auto convert pk to model, But when reuse serializer in others, it is required to have int field.
        # So we reparse this case
        created_from = data.get('created_from')
        if isinstance(created_from, int):
            data['created_from'] = POFormula.objects.get(pk=created_from)
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
        instance = super().create(validated_data)
        create_po_formula_to_data_entry(instance, data_entries)
        activity_log(POFormula, instance, 1, POFormulaSerializer, {})
        return instance

    def update(self, instance, validated_data):
        data_entries = pop(validated_data, 'self_data_entries', [])
        instance.self_data_entries.all().delete()
        create_po_formula_to_data_entry(instance, data_entries)
        activity_log(POFormula, instance, 2, POFormulaSerializer, {})
        validated_data = self.reparse(validated_data)
        return super().update(instance, validated_data)

    def to_internal_value(self, data):
        data = super().to_internal_value(data)
        if self.context.get('view'):
            from sales.views import proposal
            views = [proposal.PriceComparisonList, proposal.PriceComparisonDetail,
                     proposal.ProposalWritingList, proposal.ProposalWritingDetail]
            if any([isinstance(self.context['view'], view) for view in views]):
                created_from = data.get('created_from')
                if isinstance(created_from, POFormula):
                    data['created_from'] = created_from.pk
                assemble = data.get('assemble')
                if isinstance(assemble, Assemble):
                    data['assemble'] = assemble.pk
                group = data.get('group')
                if isinstance(group, POFormulaGrouping):
                    data['group'] = group.pk
        return data

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
                if 'catalog' in linked_description or 'estimate' in linked_description:
                    pk = linked_description.split(':')[1]
                    if 'estimate' in linked_description:
                        linked_description = DescriptionLibrary.objects.get(pk=pk)
                    else:
                        linked_description = DataPoint.objects.get(pk=pk)
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
            except (Catalog.DoesNotExist, IndexError, NameError, SyntaxError, AttributeError):
                data['catalog_ancestor'] = None
                data['catalog_link'] = []
        else:
            data['catalog_ancestor'] = None
            data['catalog_link'] = []

        data['content_type'] = PO_FORMULA_CONTENT_TYPE
        original = data.get('original')
        if not original:
            data['original'] = instance.pk
        return data


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
        instance = super().create(validated_data)
        activity_log(UnitLibrary, instance, 1, UnitLibrarySerializer, {})
        return instance

    def update(self, instance, validated_data):
        activity_log(UnitLibrary, instance, 2, UnitLibrarySerializer, {})
        return super().update(instance, validated_data)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['content_type'] = UNIT_LIBRARY_CONTENT_TYPE
        return data


class DescriptionLibrarySerializer(serializers.ModelSerializer):
    class Meta:
        model = DescriptionLibrary
        fields = ('id', 'name', 'linked_description',)

    def create(self, validated_data):
        instance = super().create(validated_data)
        activity_log(DescriptionLibrary, instance, 1, DescriptionLibrarySerializer, {})
        return instance

    def update(self, instance, validated_data):
        activity_log(DescriptionLibrary, instance, 2, DescriptionLibrarySerializer, {})
        return super().update(instance, validated_data)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['content_type'] = DESCRIPTION_LIBRARY_CONTENT_TYPE
        return data


class AssembleSerializer(serializers.ModelSerializer):
    assemble_formulas = POFormulaSerializer('assemble', many=True, required=False, allow_null=True)

    class Meta:
        model = Assemble
        fields = ('id', 'name', 'created_date', 'modified_date', 'user_create', 'user_update',
                  'assemble_formulas', 'description', 'is_show')
        extra_kwargs = extra_kwargs_for_base_model()

    def create_po_formula(self, po_formulas, instance):
        for po_formula in po_formulas:
            po_formula['assemble'] = instance.pk
            po_formula['is_show'] = False
            created_from = po_formula.get('created_from')
            if created_from:
                if isinstance(po_formula['created_from'], POFormula):
                    po_formula['created_from'] = created_from.pk
            else:
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
        activity_log(Assemble, instance, 1, AssembleSerializer, {})
        return instance

    def update(self, instance, validated_data):
        po_formulas = pop(validated_data, 'assemble_formulas', [])
        instance.assemble_formulas.all().delete()
        self.create_po_formula(po_formulas, instance)
        activity_log(Assemble, instance, 2, AssembleSerializer, {})
        return super().update(instance, validated_data)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['content_type'] = ASSEMBLE_CONTENT_TYPE
        original = data.get('original')
        if not original:
            data['original'] = instance.pk
        return data


class DataViewSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataView
        fields = ('id', 'formula', 'name', 'estimate_template')

    def to_internal_value(self, data):
        data = super().to_internal_value(data)
        if self.context.get('view'):
            from sales.views import proposal
            views = [proposal.PriceComparisonList, proposal.PriceComparisonDetail,
                     proposal.ProposalWritingList, proposal.ProposalWritingDetail]
            if any([isinstance(self.context['view'], view) for view in views]):
                estimate_template = data['estimate_template']
                if isinstance(estimate_template, EstimateTemplate):
                    data['estimate_template'] = estimate_template.pk
        return data


class EstimateTemplateSerializer(serializers.ModelSerializer):
    assembles = AssembleSerializer(many=True, required=False, allow_null=True,)
    data_views = DataViewSerializer('estimate_template', many=True, required=False, allow_null=True)
    data_entries = POFormulaToDataEntrySerializer('estimate_template', many=True, required=False, allow_null=True)

    class Meta:
        model = EstimateTemplate
        fields = '__all__'
        extra_kwargs = extra_kwargs_for_base_model()

    def reparse(self, data):
        # Serializer is auto convert pk to model, But when reuse serializer in others, it is required to have int field.
        # So we reparse this case
        from sales.views.proposal import GroupByEstimate
        group_by_proposal = data.get('group_by_proposal')
        if isinstance(group_by_proposal, int):
            data['group_by_proposal'] = GroupByEstimate.objects.get(pk=group_by_proposal)
        price_comparison = data.get('price_comparison')
        if isinstance(price_comparison, int):
            data['price_comparison'] = PriceComparison.objects.get(pk=price_comparison)
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
                if po.get('created_from'):
                    if isinstance(po['created_from'], POFormula):
                        po['created_from'] = po['created_from'].pk
            serializer = AssembleSerializer(data=assemble, context=self.context)
            serializer.is_valid(raise_exception=True)
            obj = serializer.save(is_show=False)
            pk_assembles.append(obj.pk)
        return pk_assembles

    def create_data_view(self, data_views, instance):
        for data_view in data_views:
            data_view['estimate_template'] = instance.pk
            serializer = DataViewSerializer(data=data_view)
            serializer.is_valid()
            serializer.save(estimate_template_id=instance.pk)

    def create(self, validated_data):
        assembles = pop(validated_data, 'assembles', [])
        data_views = pop(validated_data, 'data_views', [])
        data_entries = pop(validated_data, 'data_entries', [])

        pk_assembles = self.create_assembles(assembles)
        validated_data = self.reparse(validated_data)
        instance = super().create(validated_data)
        create_po_formula_to_data_entry(EstimateTemplate(name='name'), data_entries, instance.pk)
        self.create_data_view(data_views, instance)
        instance.assembles.add(*Assemble.objects.filter(pk__in=pk_assembles))
        activity_log(EstimateTemplate, instance, 1, EstimateTemplateSerializer, {})
        return instance

    def update(self, instance, validated_data):
        assembles = pop(validated_data, 'assembles', [])
        data_views = pop(validated_data, 'data_views', [])
        data_entries = pop(validated_data, 'data_entries', [])

        instance.data_entries.all().delete()
        create_po_formula_to_data_entry(EstimateTemplate(name='name'), data_entries, instance.pk)
        pk_assembles = self.create_assembles(assembles)

        validated_data = self.reparse(validated_data)
        instance = super().update(instance, validated_data)
        instance.data_views.all().delete()
        self.create_data_view(data_views, instance)

        instance.assembles.all().delete()
        instance.assembles.add(*Assemble.objects.filter(pk__in=pk_assembles))
        activity_log(EstimateTemplate, instance, 2, EstimateTemplateSerializer, {})
        return instance

    def to_internal_value(self, data):
        data = super().to_internal_value(data)
        if self.context.get('view'):
            from sales.views import proposal
            views = [proposal.PriceComparisonList, proposal.PriceComparisonDetail,
                     proposal.ProposalWritingList, proposal.ProposalWritingDetail]
            if any([isinstance(self.context['view'], view) for view in views]):
                price_comparison = data.get('price_comparison')
                if isinstance(price_comparison, proposal.PriceComparison):
                    data['price_comparison'] = price_comparison.pk
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
