from django_filters import rest_framework as filters

from sales.models import ChangeOrder, LeadDetail


class ChangeOrderFilter(filters.FilterSet):
    lead = filters.ModelMultipleChoiceFilter(method='filter_by_leads', queryset=LeadDetail.objects.all())

    class Meta:
        model = ChangeOrder
        fields = ('lead', )

    def filter_by_leads(self, queryset, name, value):
        if value:
            return queryset.filter(proposal_writing__lead__in=value).distinct()
        return queryset
