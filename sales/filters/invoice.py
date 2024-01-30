from django_filters import rest_framework as filters

from ..models import LeadDetail, Invoice


class InvoiceFilter(filters.FilterSet):
    name = filters.CharFilter(field_name='name', lookup_expr='icontains')
    created_date = filters.DateTimeFilter(field_name='created_date', lookup_expr='date')
    modified_date = filters.DateTimeFilter(field_name='modified_date', lookup_expr='date')
    proposal__lead = filters.ModelChoiceFilter(queryset=LeadDetail.objects.all())
    status = filters.MultipleChoiceFilter(choices=Invoice.InvoiceStatus.choices)
    date_paid = filters.DateTimeFilter(field_name='date_paid', lookup_expr='date')
    deadline_datetime = filters.DateTimeFilter(field_name='deadline_datetime', lookup_expr='date')

    class Meta:
        model = Invoice
        fields = ('name', 'created_date', 'modified_date', 'proposal__lead',
                  'status', 'date_paid', 'deadline_datetime')
