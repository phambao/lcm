from django_filters import rest_framework as filters

from sales.models import LeadDetail
from sales.models.lead_schedule import DailyLog


class DailyLogFilter(filters.FilterSet):
    lead_list = filters.ModelChoiceFilter(queryset=LeadDetail.objects.all())

    class Meta:
        model = DailyLog
        fields = ('lead_list',)
