from django.contrib.auth import get_user_model
from django_filters import rest_framework as filters

from sales.models import POFormula, POFormulaGrouping, Assemble, EstimateTemplate


class FormulaFilter(filters.FilterSet):
    group = filters.BooleanFilter(field_name='group', lookup_expr='isnull', exclude=True)
    assemble = filters.BooleanFilter(field_name='assemble', lookup_expr='isnull', exclude=True)
    created_date = filters.DateTimeFilter(field_name='created_date', lookup_expr='gt')
    modified_date = filters.DateTimeFilter(field_name='modified_date', lookup_expr='gt')
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
    is_show = filters.BooleanFilter(field_name='is_show', lookup_expr='isnull', exclude=True)

    class Meta:
        model = POFormula
        fields = ('group', 'assemble', 'quantity', 'formula', 'name', 'created_date', 'modified_date', 'markup',
                  'charge', 'material', 'unit', 'cost', 'gross_profit', 'description_of_formula', 'formula_scenario',
                  'user_create', 'user_update')


class EstimateTemplateFilter(filters.FilterSet):
    name = filters.CharFilter(field_name='name', lookup_expr='icontains')
    created_date = filters.DateTimeFilter(field_name='created_date', lookup_expr='gt')
    modified_date = filters.DateTimeFilter(field_name='modified_date', lookup_expr='gt')
    class Meta:
        model = EstimateTemplate
        fields = ('name', 'created_date', 'modified_date')


class AssembleFilter(filters.FilterSet):
    name = filters.CharFilter(field_name='name', lookup_expr='icontains')
    created_date = filters.DateTimeFilter(field_name='created_date', lookup_expr='gt')
    formula_name = filters.CharFilter(field_name='assemble_formulas__name', lookup_expr='icontains')
    user_create = filters.ModelMultipleChoiceFilter(queryset=get_user_model().objects.all())
    modified_date = filters.DateTimeFilter(field_name='modified_date', lookup_expr='gt')

    class Meta:
        model = Assemble
        fields = ('name', 'created_date', 'formula_name', 'user_create', 'modified_date')
