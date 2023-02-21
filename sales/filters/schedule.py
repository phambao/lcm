from django.contrib.auth import get_user_model
from django_filters import rest_framework as filters

from sales.filters.lead_list import CHOICES, FILTERS
from sales.models import LeadDetail
from sales.models.lead_schedule import DailyLog, ToDo, TagSchedule, ScheduleEvent, Priority


class DailyLogFilter(filters.FilterSet):
    lead_list = filters.ModelChoiceFilter(queryset=LeadDetail.objects.all())
    tags = filters.ModelMultipleChoiceFilter(queryset=TagSchedule.objects.all())
    to_dos = filters.ModelMultipleChoiceFilter(queryset=ToDo.objects.all())
    internal_user_share = filters.BooleanFilter('internal_user_share')
    internal_user_notify = filters.BooleanFilter('internal_user_notify')
    owner_share = filters.BooleanFilter('owner_share')
    owner_notify = filters.BooleanFilter('owner_notify')
    private_share = filters.BooleanFilter('private_share')
    private_notify = filters.BooleanFilter('private_notify')
    event = filters.ModelChoiceFilter(queryset=ScheduleEvent.objects.all())
    # date = filters.DateRangeFilter(field_name='date', choices=CHOICES, filters=FILTERS)
    start_day = filters.DateTimeFilter(field_name='date', lookup_expr='gte')
    end_day = filters.DateTimeFilter(field_name='date', lookup_expr='lte')

    class Meta:
        model = DailyLog
        fields = ('lead_list', 'tags', 'to_dos', 'internal_user_share', 'internal_user_notify',
                  'owner_share', 'owner_notify', 'private_share', 'private_notify', 'event', 'start_day', 'end_day')


class EventFilter(filters.FilterSet):
    lead_list = filters.ModelChoiceFilter(queryset=LeadDetail.objects.all())
    event_title = filters.CharFilter(field_name="event_title", lookup_expr='icontains')
    assigned_user = filters.ModelMultipleChoiceFilter(queryset=get_user_model().objects.all())
    reminder = filters.NumberFilter()
    start_day = filters.DateFilter(field_name='start_day', lookup_expr='gte')
    end_day = filters.DateFilter(field_name='start_day', lookup_expr='lte')
    start_hour = filters.DateTimeFilter(field_name='start_hour', lookup_expr='gte')
    end_hour = filters.DateTimeFilter(field_name='end_hour', lookup_expr='lte')
    is_before = filters.BooleanFilter('is_before')
    is_after = filters.BooleanFilter('is_after')
    predecessor = filters.ModelChoiceFilter(queryset=ScheduleEvent.objects.all())
    tags = filters.ModelMultipleChoiceFilter(queryset=TagSchedule.objects.all())
    todo = filters.ModelChoiceFilter(queryset=ToDo.objects.all())
    daily_log = filters.ModelChoiceFilter(queryset=DailyLog.objects.all())

    class Meta:
        model = ScheduleEvent
        fields = ('lead_list', 'event_title', 'assigned_user', 'reminder', 'start_day',
                  'end_day', 'start_hour', 'is_before', 'is_after', 'predecessor', 'tags', 'todo', 'daily_log')


class ToDoFilter(filters.FilterSet):
    lead_list = filters.ModelChoiceFilter(queryset=LeadDetail.objects.all())
    title = filters.CharFilter(field_name="title", lookup_expr='icontains')
    priority = filters.ChoiceFilter(choices=Priority.choices)
    due_date = filters.DateRangeFilter(field_name='due_date', choices=CHOICES, filters=FILTERS)
    start_day = filters.DateTimeFilter(field_name='due_date', lookup_expr='gte')
    end_day = filters.DateTimeFilter(field_name='due_date', lookup_expr='lte')
    time_hour = filters.DateTimeFilter(field_name='time_hour')
    is_complete = filters.BooleanFilter('is_complete')
    sync_due_date = filters.DateTimeFilter(field_name='sync_due_date')
    reminder = filters.NumberFilter()
    assigned_to = filters.ModelMultipleChoiceFilter(queryset=get_user_model().objects.all())
    tags = filters.ModelMultipleChoiceFilter(queryset=TagSchedule.objects.all())
    event = filters.ModelChoiceFilter(queryset=ScheduleEvent.objects.all())
    daily_log = filters.ModelChoiceFilter(queryset=DailyLog.objects.all())

    class Meta:
        model = ToDo
        fields = ('lead_list', 'title', 'priority', 'due_date', 'time_hour', 'start_day', 'end_day',
                  'is_complete', 'sync_due_date', 'reminder', 'assigned_to', 'tags', 'event', 'daily_log')