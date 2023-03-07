from rest_framework import serializers

from base.serializers.base import IDAndNameSerializer
from base.utils import pop, activity_log
from sales.models.estimate import POFormula, POFormulaGrouping, DataEntry, POFormulaToDataEntry, TemplateName, \
    UnitLibrary


class DataEntrySerializer(serializers.ModelSerializer):
    unit = IDAndNameSerializer(required=False, allow_null=True)

    class Meta:
        model = DataEntry
        fields = ('id', 'name', 'value', 'unit')
        extra_kwargs = {'id': {'read_only': False, 'required': False}}

    def create(self, validated_data):
        unit = pop(validated_data, 'unit', {})
        validated_data['unit_id'] = unit.get('id', None)
        return super(DataEntrySerializer, self).create(validated_data)

    def update(self, instance, validated_data):
        unit = pop(validated_data, 'unit', {})
        validated_data['unit_id'] = unit.get('id', None)
        return super().update(instance, validated_data)


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
        fields = ('id', 'name', 'formula', 'text_formula', 'type', 'groups', 'self_data_entries',
                  'description', 'quantity', 'markup', 'charge', 'material', 'unit', 'show_color')

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
