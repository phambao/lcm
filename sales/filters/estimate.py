from django_filters import rest_framework as filters

from sales.models import POFormula, POFormulaGrouping, Assemble


class FormulaFilter(filters.FilterSet):
    group = filters.BooleanFilter(field_name='group', lookup_expr='isnull', exclude=True)
    assemble = filters.BooleanFilter(field_name='assemble', lookup_expr='isnull', exclude=True)

    class Meta:
        model = POFormula
        fields = ('group', 'assemble')
