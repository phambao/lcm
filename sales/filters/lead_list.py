from django.contrib.auth import get_user_model
from django_filters import rest_framework as filters
from ..models.lead_list import Contact, Activities, LeadDetail, TagActivity, PhaseActivity
from base.filters import CountryStateCityBaseFilter


class LeadDetailFilter(filters.FilterSet, CountryStateCityBaseFilter):
    lead_title = filters.CharFilter(field_name='lead_title', lookup_expr='icontains')
    salesperson = filters.ModelMultipleChoiceFilter(queryset=get_user_model().objects.all())
    status = filters.MultipleChoiceFilter(choices=LeadDetail.Status.choices)
    proposal_status = filters.MultipleChoiceFilter(choices=LeadDetail.ProposalStatus.choices)
    city = filters.NumberFilter(method='filter_city_id')
    state = filters.NumberFilter(method='filter_state_id')
    country = filters.NumberFilter(method='filter_country_id')

    class Meta:
        model = LeadDetail
        fields = ('lead_title', 'salesperson', 'status', 'proposal_status', 'city', 'state', 'country')


class ContactsFilter(filters.FilterSet, CountryStateCityBaseFilter):
    first_name = filters.CharFilter(field_name="first_name", lookup_expr='icontains')
    last_name = filters.CharFilter(field_name="last_name", lookup_expr='icontains')
    email = filters.CharFilter(field_name="email", lookup_expr='icontains')
    phone_number = filters.CharFilter(field_name="phone_contacts__phone_number", lookup_expr='icontains')
    city = filters.NumberFilter(method='filter_city_id')
    state = filters.NumberFilter(method='filter_state_id')
    country = filters.NumberFilter(method='filter_country_id')
    
    class Meta:
        model = Contact
        fields = ('first_name', 'last_name', 'email', 'phone_contacts', 'city', 'state', 'country')


class ActivitiesFilter(filters.FilterSet):
    status = filters.MultipleChoiceFilter(choices=Activities.Status.choices)
    tags = filters.ModelMultipleChoiceFilter(queryset=TagActivity.objects.all())
    phase = filters.ModelChoiceFilter(queryset=PhaseActivity.objects.all())
    assigned_to = filters.CharFilter(field_name='assigned_to', lookup_expr='icontains')
    attendees = filters.BooleanFilter(field_name='attendees', lookup_expr='isnull')
    start_date = filters.DateFilter(field_name='start_date', lookup_expr='gte')
    end_date = filters.DateFilter(field_name='end_date', lookup_expr='lte')

    class Meta:
        model = Activities
        fields = ('status', 'tags', 'phase', 'assigned_to', 'start_date', 'end_date')
