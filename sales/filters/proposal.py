from django_filters import rest_framework as filters

from ..models import PriceComparison, ProposalWriting, ProposalTemplate, LeadDetail


class PriceComparisonFilter(filters.FilterSet):
    name = filters.CharFilter(field_name='name', lookup_expr='icontains')
    created_date = filters.DateTimeFilter(field_name='created_date', lookup_expr='date')
    modified_date = filters.DateTimeFilter(field_name='modified_date', lookup_expr='date')
    lead = filters.ModelChoiceFilter(queryset=LeadDetail.objects.all())

    class Meta:
        model = PriceComparison
        fields = ('name', 'created_date', 'modified_date', 'lead')


class ProposalWritingFilter(filters.FilterSet):
    name = filters.CharFilter(field_name='name', lookup_expr='icontains')
    created_date = filters.DateTimeFilter(field_name='created_date', lookup_expr='date')
    modified_date = filters.DateTimeFilter(field_name='modified_date', lookup_expr='date')
    total_project_cost_min = filters.NumberFilter(field_name='total_project_cost', lookup_expr='gte')
    total_project_cost_max = filters.NumberFilter(field_name='total_project_cost', lookup_expr='lte')
    avg_markup_min = filters.NumberFilter(field_name='avg_markup', lookup_expr='gte')
    avg_markup_max = filters.NumberFilter(field_name='avg_markup', lookup_expr='lte')
    lead = filters.ModelChoiceFilter(queryset=LeadDetail.objects.all())

    class Meta:
        model = ProposalWriting
        fields = ('name', 'created_date', 'modified_date', 'total_project_cost', 'avg_markup', 'lead')


class ProposalTemplateFilter(filters.FilterSet):
    name = filters.CharFilter(field_name='name', lookup_expr='icontains')

    class Meta:
        model = ProposalTemplate
        fields = ('name',)