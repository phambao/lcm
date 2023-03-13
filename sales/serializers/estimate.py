from rest_framework import serializers
from django.contrib.contenttypes.models import ContentType

from base.serializers.base import IDAndNameSerializer
from base.utils import pop, activity_log
from sales.models import DataPoint
from sales.models.estimate import POFormula, POFormulaGrouping, DataEntry, POFormulaToDataEntry, TemplateName, \
    UnitLibrary, DescriptionLibrary


PO_FORMULA_CONTENT_TYPE = ContentType.objects.get_for_model(POFormula).pk
DATA_ENTRY_CONTENT_TYPE = ContentType.objects.get_for_model(DataEntry).pk
UNIT_LIBRARY_CONTENT_TYPE = ContentType.objects.get_for_model(UnitLibrary).pk
DESCRIPTION_LIBRARY_CONTENT_TYPE = ContentType.objects.get_for_model(DescriptionLibrary).pk


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

    class Meta:
        model = DataEntry
        fields = ('id', 'name', 'value', 'unit')
        extra_kwargs = {'id': {'read_only': False, 'required': False}}

    def create(self, validated_data):
        unit = pop(validated_data, 'unit', {})
        validated_data['unit_id'] = unit.get('id', None)
        instance = super().create(validated_data)
        activity_log(DataEntry, instance, 1, DataEntrySerializer, {})
        return instance

    def update(self, instance, validated_data):
        unit = pop(validated_data, 'unit', {})
        validated_data['unit_id'] = unit.get('id', None)
        activity_log(DataEntry, instance, 2, DataEntrySerializer, {})
        return super().update(instance, validated_data)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['content_type'] = DATA_ENTRY_CONTENT_TYPE
        return data


class POFormulaToDataEntrySerializer(serializers.ModelSerializer):
    data_entry = DataEntrySerializer(allow_null=True, required=False)

    class Meta:
        model = POFormulaToDataEntry
        fields = ('id', 'value', 'data_entry',)

    def to_representation(self, instance):
        data = super(POFormulaToDataEntrySerializer, self).to_representation(instance)
        return data


def create_po_formula_to_data_entry(instance, data_entries):
    data = []
    for data_entry in data_entries:
        params = {"po_formula_id": instance.pk, "value": data_entry['value']}
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
        fields = ('id', 'name', 'formula', 'type', 'groups', 'self_data_entries',
                  'linked_description', 'quantity', 'markup', 'charge', 'material', 'unit', 'show_color')

    def create(self, validated_data):
        data_entries = pop(validated_data, 'self_data_entries', [])
        instance = super().create(validated_data)
        create_po_formula_to_data_entry(instance, data_entries)
        activity_log(POFormula, instance, 1, POFormulaSerializer, {})
        return instance

    def update(self, instance, validated_data):
        data_entries = pop(validated_data, 'self_data_entries', [])
        instance.self_data_entries.all().delete()
        create_po_formula_to_data_entry(instance, data_entries)
        activity_log(POFormula, instance, 2, POFormulaSerializer, {})
        return super().update(instance, validated_data)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if 'catalog' in data['linked_description'] or 'estimate' in data['linked_description']:
            pk = data['linked_description'].split(':')[1]
            if 'estimate' in data['linked_description']:
                linked_description = DescriptionLibrary.objects.get(pk=pk)
            else:
                linked_description = DataPoint.objects.get(pk=pk)
            data['linked_description'] = LinkedDescriptionSerializer(linked_description).data
        data['content_type'] = PO_FORMULA_CONTENT_TYPE
        return data


class POFormulaGroupingSerializer(serializers.ModelSerializer):
    po_formula_groupings = POFormulaSerializer('groups', many=True,
                                               allow_null=True, required=False)

    class Meta:
        model = POFormulaGrouping
        fields = ('id', 'name', 'po_formula_groupings')

    def create(self, validated_data):
        po_formulas = pop(validated_data, 'po_formula_groupings', [])
        instance = super().create(validated_data)
        data = []
        for po_formula in po_formulas:
            po_formula['group'] = instance
            data.append(POFormula(**po_formula))
        POFormula.objects.bulk_create(data)
        return instance

    def update(self, instance, validated_data):
        po_formulas = pop(validated_data, 'po_formula_groupings', [])
        instance.po_formula_groupings.all().delete()
        data = []
        for po_formula in po_formulas:
            po_formula['group'] = instance
            data.append(POFormula(**po_formula))
        POFormula.objects.bulk_create(data)
        return super(POFormulaGroupingSerializer, self).update(instance, validated_data)


class TemplateNameSerializer(serializers.ModelSerializer):
    class Meta:
        model = TemplateName
        fields = '__all__'
        extra_kwargs = {'user_create': {'read_only': True},
                        'user_update': {'read_only': True}}


class UnitLibrarySerializer(serializers.ModelSerializer):
    class Meta:
        model = UnitLibrary
        fields = ('id', 'name',)

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
