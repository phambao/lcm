from django.contrib.auth import get_user_model
from django_filters import rest_framework as filters

from sales.models import POFormula, POFormulaGrouping, Assemble, EstimateTemplate


class FormulaFilter(filters.FilterSet):
    group = filters.BooleanFilter(field_name='group', lookup_expr='isnull', exclude=True)
    assemble = filters.BooleanFilter(field_name='assemble', lookup_expr='isnull', exclude=True)

    class Meta:
        model = POFormula
        fields = ('group', 'assemble')


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

    class Meta:
        model = Assemble
        fields = ('name', 'created_date', 'formula_name', 'user_create')
