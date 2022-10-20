from django_filters import rest_framework as filters
from ..models.lead_list import Contact, Activities


class ContactsFilter(filters.FilterSet):
    first_name = filters.CharFilter(field_name="first_name", lookup_expr='icontains')
    last_name = filters.CharFilter(field_name="last_name", lookup_expr='icontains')
    email = filters.CharFilter(field_name="email", lookup_expr='icontains')
    phone_number = filters.CharFilter(field_name="phone_contacts__phone_number", lookup_expr='icontains')
    city = filters.CharFilter(field_name="city__name", lookup_expr='icontains')
    state = filters.CharFilter(field_name="state__name", lookup_expr='icontains')
    country = filters.CharFilter(field_name="country__name", lookup_expr='icontains')
    
    class Meta:
        model = Contact
        fields = ('first_name', 'last_name', 'email', 'phone_contacts', 'city', 'state', 'country')


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
