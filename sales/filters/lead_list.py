from django_filters import rest_framework as filters
from ..models.lead_list import Activities


class ActivitiesFilter(filters.FilterSet):
    status = filters.MultipleChoiceFilter(choices=Activities.Status.choices)
    tag = filters.MultipleChoiceFilter(choices=Activities.Tags.choices)
    phase = filters.MultipleChoiceFilter(choices=Activities.Phases.choices)
    assigned_to = filters.CharFilter(field_name='assigned_to', lookup_expr='icontains')
    start_date = filters.DateFilter(field_name='start_date', lookup_expr='gte')
    end_date = filters.DateFilter(field_name='end_date', lookup_expr='lte')
    
    class Meta:
        model = Activities
        fields = ('status', 'tag', 'phase', 'assigned_to', 'start_date', 'end_date')
