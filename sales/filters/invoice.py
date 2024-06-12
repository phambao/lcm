from django_filters import rest_framework as filters

from ..models import LeadDetail, Invoice


class InvoiceFilter(filters.FilterSet):
    name = filters.CharFilter(field_name='name', lookup_expr='icontains')
    created_date = filters.DateTimeFilter(field_name='created_date', lookup_expr='date')
    modified_date = filters.DateTimeFilter(field_name='modified_date', lookup_expr='date')
    lead = filters.ModelChoiceFilter(queryset=LeadDetail.objects.all(), field_name='proposal__lead')
    status = filters.MultipleChoiceFilter(choices=Invoice.InvoiceStatus.choices)
    date_paid = filters.DateTimeFilter(field_name='date_paid', lookup_expr='date')
    deadline_datetime = filters.DateTimeFilter(field_name='deadline_datetime', lookup_expr='date')
    lead_name = filters.CharFilter(field_name='proposal__lead__lead_title', lookup_expr='icontains')

    class Meta:
        model = Invoice
        fields = ('name', 'created_date', 'modified_date', 'lead',
                  'status', 'date_paid', 'deadline_datetime', 'lead_name')
