from django_filters import rest_framework as filters
from django.contrib.auth import get_user_model

from sales.models import ChangeOrder, LeadDetail


class ChangeOrderFilter(filters.FilterSet):
    lead = filters.ModelMultipleChoiceFilter(method='filter_by_leads', queryset=LeadDetail.objects.all())
    name = filters.CharFilter(field_name='name', lookup_expr='icontains')
    created_date = filters.DateTimeFilter(field_name='created_date', lookup_expr='date')
    modified_date = filters.DateTimeFilter(field_name='modified_date', lookup_expr='date')
    user_create = filters.ModelMultipleChoiceFilter(queryset=get_user_model().objects.all())
    user_update = filters.ModelMultipleChoiceFilter(queryset=get_user_model().objects.all())

    class Meta:
        model = ChangeOrder
        fields = ('lead', 'name', 'created_date', 'modified_date', 'user_create', 'user_update')

    def filter_by_leads(self, queryset, name, value):
        if value:
            return queryset.filter(proposal_writing__lead__in=value).distinct()
        return queryset
