from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils.timezone import now
from django_filters import rest_framework as filters
from django_filters.filters import _truncate

from ..models import lead_list
from ..models.lead_list import Contact, Activities, LeadDetail, TagActivity, PhaseActivity, Communication, Status

CHOICES = [
    ("today", "Today"),
    ("yesterday", "Yesterday"),
    ("past-7-days", "Past 7 days"),
    ("past-14-days", "Past 14 days"),
    ("past-30-days", "Past 30 days"),
    ("past-45-days", "Past 45 days"),
    ("past-90-days", "Past 90 days"),
]

FILTERS = {
    "today": lambda qs, name: qs.filter(
        **{
            "%s__year" % name: now().year,
            "%s__month" % name: now().month,
            "%s__day" % name: now().day,
        }
    ),
    "yesterday": lambda qs, name: qs.filter(
        **{
            "%s__gte" % name: now() - timedelta(days=1),
            "%s__lt" % name: now(),
        }
    ),
    "past-7-days": lambda qs, name: qs.filter(
        **{
            "%s__gte" % name: _truncate(now() - timedelta(days=7)),
            "%s__lt" % name: _truncate(now() + timedelta(days=1)),
        }
    ),
    "past-14-days": lambda qs, name: qs.filter(
        **{
            "%s__gte" % name: _truncate(now() - timedelta(days=14)),
            "%s__lt" % name: _truncate(now() + timedelta(days=1)),
        }
    ),
    "past-30-days": lambda qs, name: qs.filter(
        **{
            "%s__gte" % name: _truncate(now() - timedelta(days=30)),
            "%s__lt" % name: _truncate(now() + timedelta(days=1)),
        }
    ),
    "past-45-days": lambda qs, name: qs.filter(
        **{
            "%s__gte" % name: _truncate(now() - timedelta(days=45)),
            "%s__lt" % name: _truncate(now() + timedelta(days=1)),
        }
    ),
    "past-90-days": lambda qs, name: qs.filter(
        **{
            "%s__gte" % name: _truncate(now() - timedelta(days=90)),
            "%s__lt" % name: _truncate(now() + timedelta(days=1)),
        }
    ),
}


class LeadDetailFilter(filters.FilterSet):
    id = filters.ModelMultipleChoiceFilter(method='filter_by_leads', queryset=LeadDetail.objects.all())
    lead_title = filters.CharFilter(field_name='lead_title', lookup_expr='icontains')
    salesperson = filters.ModelMultipleChoiceFilter(queryset=get_user_model().objects.all())
    status = filters.MultipleChoiceFilter(choices=LeadDetail.Status.choices)
    tags = filters.ModelMultipleChoiceFilter(queryset=lead_list.TagLead.objects.all())
    project_types = filters.ModelMultipleChoiceFilter(queryset=lead_list.ProjectType.objects.all())
    proposal_status = filters.MultipleChoiceFilter(choices=LeadDetail.ProposalStatus.choices)
    age_of_lead = filters.DateRangeFilter(field_name='created_date', choices=CHOICES, filters=FILTERS)
    sold_date = filters.DateRangeFilter(field_name='projected_sale_date', choices=CHOICES, filters=FILTERS)
    most_recent_click = filters.DateRangeFilter(field_name='recent_click', choices=CHOICES, filters=FILTERS)
    most_of_click = filters.NumberFilter(field_name='number_of_click', lookup_expr='gt')
    sources = filters.ModelMultipleChoiceFilter(queryset=lead_list.SourceLead.objects.all())
    has_valid_email = filters.BooleanFilter(method='filter_has_valid_email', label='Has Valid Email')

    class Meta:
        model = LeadDetail
        fields = ('lead_title', 'salesperson', 'status', 'tags', 'project_types',
                  'proposal_status', 'age_of_lead', 'sold_date', 'most_recent_click',
                  'most_of_click', 'sources', 'has_valid_email')

    def filter_has_valid_email(self, queryset, name, value):
        valid_email = r'^[a-zA-Z0-9\_\.\+\-]+@[a-zA-Z0-9\-]+\.[a-zA-Z0-9\-\.]+$'
        if value:
            return queryset.filter(contacts__email__regex=valid_email).distinct()
        return queryset.exclude(contacts__email__regex=valid_email).distinct()

    
    def filter_by_leads(self, queryset, name, value):
        if value:
            queryset = queryset.filter(id__in=[lead.id for lead in value])
            return queryset.distinct()
        return queryset


class ContactsFilter(filters.FilterSet):
    first_name = filters.CharFilter(field_name="first_name", lookup_expr='icontains')
    last_name = filters.CharFilter(field_name="last_name", lookup_expr='icontains')
    email = filters.CharFilter(field_name="email", lookup_expr='icontains')
    phone_number = filters.CharFilter(field_name="phone_contacts__phone_number", lookup_expr='icontains')
    city = filters.CharFilter(field_name="city", lookup_expr='icontains')
    state = filters.CharFilter(field_name="state", lookup_expr='icontains')
    country = filters.CharFilter(field_name="country", lookup_expr='icontains')

    class Meta:
        model = Contact
        fields = ('first_name', 'last_name', 'email', 'phone_contacts', 'city', 'state', 'country')


class ActivitiesFilter(filters.FilterSet):
    status = filters.MultipleChoiceFilter(choices=Activities.Status.choices)
    tags = filters.ModelMultipleChoiceFilter(queryset=TagActivity.objects.all())
    phase = filters.ModelChoiceFilter(queryset=PhaseActivity.objects.all())
    assigned_to = filters.ModelMultipleChoiceFilter(queryset=get_user_model().objects.all())
    attendees = filters.ModelMultipleChoiceFilter(queryset=get_user_model().objects.all())
    start_date = filters.DateFilter(field_name='start_date', lookup_expr='gte')
    end_date = filters.DateFilter(field_name='end_date', lookup_expr='lte')
    title = filters.CharFilter(field_name='title', lookup_expr='icontains')

    class Meta:
        model = Activities
        fields = ('title', 'status', 'tags', 'phase', 'assigned_to', 'start_date', 'end_date')


class CommunicationFilter(filters.FilterSet):
    lead = filters.ModelChoiceFilter(queryset=LeadDetail.objects.all())
    type = filters.MultipleChoiceFilter(choices=Status.choices)

    class Meta:
        model = Communication
        fields = ('lead', 'number', 'last_date', 'type')
