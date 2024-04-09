from django.contrib.auth import get_user_model
from django_filters import rest_framework as filters

from sales.models import POFormula, POFormulaGrouping, Assemble, EstimateTemplate, DataEntry, DescriptionLibrary, UnitLibrary
from sales.filters.lead_list import CHOICES, FILTERS


class FilterIDMixin:

    def get_by_id(self, query, name, value):
        if value:
            return query.filter(pk__in=[v.id for v in value])
        else:
            return query


class FormulaFilter(filters.FilterSet, FilterIDMixin):
    group = filters.BooleanFilter(field_name='group', lookup_expr='isnull', exclude=True)
    assemble = filters.BooleanFilter(field_name='assemble', lookup_expr='isnull', exclude=True)
    created_date = filters.DateTimeFilter(field_name='created_date', lookup_expr='date')
    modified_date = filters.DateTimeFilter(field_name='modified_date', lookup_expr='date')
    name = filters.CharFilter(field_name='name', lookup_expr='icontains')
    formula = filters.CharFilter(field_name='formula', lookup_expr='icontains')
    quantity = filters.CharFilter(field_name='quantity', lookup_expr='icontains')
    markup = filters.CharFilter(field_name='markup', lookup_expr='icontains')
    charge = filters.CharFilter(field_name='charge', lookup_expr='icontains')
    material = filters.CharFilter(field_name='material', lookup_expr='icontains')
    unit = filters.CharFilter(field_name='unit', lookup_expr='icontains')
    gross_profit = filters.CharFilter(field_name='gross_profit', lookup_expr='icontains')
    description_of_formula = filters.CharFilter(field_name='description_of_formula', lookup_expr='icontains')
    formula_scenario = filters.CharFilter(field_name='formula_scenario', lookup_expr='icontains')
    cost = filters.NumberFilter(field_name='cost', lookup_expr='gt')
    user_create = filters.ModelMultipleChoiceFilter(queryset=get_user_model().objects.all())
    user_update = filters.ModelMultipleChoiceFilter(queryset=get_user_model().objects.all())
    is_show = filters.BooleanFilter(field_name='is_show')
    age_of_formula = filters.DateRangeFilter(field_name='created_date', choices=CHOICES, filters=FILTERS)
    id = filters.ModelMultipleChoiceFilter(queryset=POFormula.objects.filter(is_show=True), field_name='id', method='get_by_id')
    data_entry = filters.ModelMultipleChoiceFilter(queryset=DataEntry.objects.all(), method='get_related_formula')

    class Meta:
        model = POFormula
        fields = ('group', 'assemble', 'quantity', 'formula', 'name', 'created_date', 'modified_date', 'markup',
                  'charge', 'material', 'unit', 'cost', 'gross_profit', 'description_of_formula', 'formula_scenario',
                  'user_create', 'user_update', 'id')

    def get_related_formula(self, query, name, value):
        if value:
            return query.filter(is_show=True, self_data_entries__data_entry__in=value).distinct()
        else:
            return query


class GroupFormulaFilter(filters.FilterSet):

    created_date = filters.DateTimeFilter(field_name='created_date', lookup_expr='date')
    modified_date = filters.DateTimeFilter(field_name='modified_date', lookup_expr='date')
    name = filters.CharFilter(field_name='group_formulas__name', lookup_expr='icontains')
    formula = filters.CharFilter(field_name='group_formulas__formula', lookup_expr='icontains')
    quantity = filters.CharFilter(field_name='group_formulas__quantity', lookup_expr='icontains')
    markup = filters.CharFilter(field_name='group_formulas__markup', lookup_expr='icontains')
    charge = filters.CharFilter(field_name='group_formulas__charge', lookup_expr='icontains')
    material = filters.CharFilter(field_name='group_formulas__material', lookup_expr='icontains')
    unit = filters.CharFilter(field_name='group_formulas__unit', lookup_expr='icontains')
    gross_profit = filters.CharFilter(field_name='group_formulas__gross_profit', lookup_expr='icontains')
    description_of_formula = filters.CharFilter(field_name='group_formulas__description_of_formula', lookup_expr='icontains')
    formula_scenario = filters.CharFilter(field_name='group_formulas__formula_scenario', lookup_expr='icontains')
    cost = filters.NumberFilter(field_name='group_formulas__cost', lookup_expr='gt')
    user_create = filters.ModelMultipleChoiceFilter(queryset=get_user_model().objects.all())
    user_update = filters.ModelMultipleChoiceFilter(queryset=get_user_model().objects.all())

    class Meta:
        model = POFormulaGrouping
        fields = ('quantity', 'name', 'formula', 'created_date', 'modified_date', 'markup',
                  'charge', 'material', 'unit', 'cost', 'gross_profit', 'description_of_formula', 'formula_scenario',
                  'user_create', 'user_update')


class EstimateTemplateFilter(filters.FilterSet, FilterIDMixin):
    name = filters.CharFilter(field_name='name', lookup_expr='icontains')
    created_date = filters.DateTimeFilter(field_name='created_date', lookup_expr='date')
    modified_date = filters.DateTimeFilter(field_name='modified_date', lookup_expr='date')
    is_show = filters.BooleanFilter(field_name='is_show')
    id = filters.ModelMultipleChoiceFilter(queryset=EstimateTemplate.objects.filter(is_show=True), field_name='id',
                                           method='get_by_id')
    assemble = filters.ModelMultipleChoiceFilter(queryset=Assemble.objects.filter(is_show=True), method='get_related_assembles')

    class Meta:
        model = EstimateTemplate
        fields = ('name', 'created_date', 'modified_date', 'assemble')

    def get_related_assembles(self, query, name, value):
        if value:
            return query.filter(is_show=True, assembles__original__in=[v.id for v in value]).distinct()
        else:
            return query


class AssembleFilter(filters.FilterSet, FilterIDMixin):
    name = filters.CharFilter(field_name='name', lookup_expr='icontains')
    created_date = filters.DateTimeFilter(field_name='created_date', lookup_expr='date')
    formula_name = filters.CharFilter(field_name='assemble_formulas__name', lookup_expr='icontains')
    user_create = filters.ModelMultipleChoiceFilter(queryset=get_user_model().objects.all())
    modified_date = filters.DateTimeFilter(field_name='modified_date', lookup_expr='date')
    id = filters.ModelMultipleChoiceFilter(queryset=Assemble.objects.filter(is_show=True), field_name='id',
                                           method='get_by_id')
    formula = filters.ModelMultipleChoiceFilter(queryset=POFormula.objects.filter(is_show=True), method='get_related_formula')

    class Meta:
        model = Assemble
        fields = ('name', 'created_date', 'formula_name', 'user_create', 'modified_date', 'id', 'formula')

    def get_related_formula(self, query, name, value):
        if value:
            return query.filter(is_show=True, assemble_formulas__original__in=[v.id for v in value]).distinct()
        else:
            return query


class DataEntryFilter(filters.FilterSet):
    name = filters.CharFilter(field_name='name', lookup_expr='icontains')
    created_date = filters.DateTimeFilter(field_name='created_date', lookup_expr='date')
    modified_date = filters.DateTimeFilter(field_name='modified_date', lookup_expr='date')
    unit = filters.ModelMultipleChoiceFilter(queryset=UnitLibrary.objects.all())
    is_dropdown = filters.BooleanFilter(field_name='is_dropdown')
    is_material_selection = filters.BooleanFilter(field_name='is_material_selection')

    class Meta:
        model = DataEntry
        fields = ('name', 'created_date', 'modified_date', 'unit', 'is_dropdown', 'is_material_selection')


class DescriptionFilter(filters.FilterSet):
    name = filters.CharFilter(field_name='name', lookup_expr='icontains')
    linked_description = filters.CharFilter(field_name='linked_description', lookup_expr='icontains')
    created_date = filters.DateTimeFilter(field_name='created_date', lookup_expr='date')
    modified_date = filters.DateTimeFilter(field_name='modified_date', lookup_expr='date')

    class Meta:
        model = DescriptionLibrary
        fields = ('name', 'linked_description', 'created_date', 'modified_date')


class UnitFilter(filters.FilterSet):
    name = filters.CharFilter(field_name='name', lookup_expr='icontains')
    description = filters.CharFilter(field_name='description', lookup_expr='icontains')
    created_date = filters.DateTimeFilter(field_name='created_date', lookup_expr='date')
    modified_date = filters.DateTimeFilter(field_name='modified_date', lookup_expr='date')

    class Meta:
        model = UnitLibrary
        fields = ('name', 'description', 'created_date', 'modified_date')
