from django_filters import rest_framework as filters

from ..models.proposal import PriceComparison, ProposalWriting


class PriceComparisonFilter(filters.FilterSet):
    name = filters.CharFilter(field_name='name', lookup_expr='icontains')
    created_date = filters.DateTimeFilter(field_name='created_date', lookup_expr='gt')
    modified_date = filters.DateTimeFilter(field_name='modified_date', lookup_expr='gt')

    class Meta:
        model = PriceComparison
        fields = ('name', 'created_date', 'modified_date')


class ProposalWritingFilter(filters.FilterSet):
    name = filters.CharFilter(field_name='name', lookup_expr='icontains')
    created_date = filters.DateTimeFilter(field_name='created_date', lookup_expr='gt')
    modified_date = filters.DateTimeFilter(field_name='modified_date', lookup_expr='gt')

    class Meta:
        model = ProposalWriting
        fields = ('name', 'created_date', 'modified_date')
