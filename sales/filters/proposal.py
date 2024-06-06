from django_filters import rest_framework as filters

from sales.models.estimate import EstimateTemplate
from ..models import PriceComparison, ProposalWriting, ProposalTemplate, LeadDetail, Job


class PriceComparisonFilter(filters.FilterSet):
    name = filters.CharFilter(field_name='name', lookup_expr='icontains')
    created_date = filters.DateTimeFilter(field_name='created_date', lookup_expr='date')
    modified_date = filters.DateTimeFilter(field_name='modified_date', lookup_expr='date')
    lead = filters.ModelChoiceFilter(queryset=LeadDetail.objects.all())
    estimate = filters.ModelMultipleChoiceFilter(queryset=EstimateTemplate.objects.filter(is_show=True), method='get_related_estimate')

    class Meta:
        model = PriceComparison
        fields = ('name', 'created_date', 'modified_date', 'lead', 'estimate')

    def get_related_estimate(self, query, name, value):
        if value:
            return query.filter(groups__estimate_templates__original__in=[v.id for v in value]).distinct()
        else:
            return query


class ProposalWritingFilter(filters.FilterSet):
    name = filters.CharFilter(field_name='name', lookup_expr='icontains')
    created_date = filters.DateTimeFilter(field_name='created_date', lookup_expr='date')
    modified_date = filters.DateTimeFilter(field_name='modified_date', lookup_expr='date')
    total_project_cost_min = filters.NumberFilter(field_name='total_project_cost', lookup_expr='gte')
    total_project_cost_max = filters.NumberFilter(field_name='total_project_cost', lookup_expr='lte')
    avg_markup_min = filters.NumberFilter(field_name='avg_markup', lookup_expr='gte')
    avg_markup_max = filters.NumberFilter(field_name='avg_markup', lookup_expr='lte')
    lead = filters.ModelChoiceFilter(queryset=LeadDetail.objects.all())
    estimate = filters.ModelMultipleChoiceFilter(queryset=EstimateTemplate.objects.filter(is_show=True), method='get_related_estimate')
    job = filters.ModelChoiceFilter(queryset=Job.objects.all())

    class Meta:
        model = ProposalWriting
        fields = ('name', 'created_date', 'modified_date', 'total_project_cost', 'avg_markup', 'lead', 'estimate', 'job')

    def get_related_estimate(self, query, name, value):
        if value:
            return query.filter(writing_groups__estimate_templates__original__in=[v.id for v in value]).distinct()
        else:
            return query


class ProposalTemplateFilter(filters.FilterSet):
    name = filters.CharFilter(field_name='name', lookup_expr='icontains')
    is_default = filters.BooleanFilter('is_default')
    default = filters.BooleanFilter(method='get_default')

    class Meta:
        model = ProposalTemplate
        fields = ('name', 'default')

    def get_default(self, queryset, name, value):
        if value:
            if queryset.filter(is_default=True).exists():
                return queryset.filter(is_default=True)
            else:
                element = queryset.first()
                if element:
                    element.is_default = True
                    element.save(update_fields=['is_default'])
                    return queryset.filter(is_default=True)
        return queryset
