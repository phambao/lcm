from django.shortcuts import get_object_or_404
from django.conf import settings
from django.template.loader import render_to_string
from django.apps import apps
from rest_framework import generics, permissions
from rest_framework import status, filters as rf_filters
from rest_framework.response import Response
from rest_framework.decorators import api_view
from django_filters import rest_framework as filters

from base.permissions import InvoicePermissions
from base.serializers.config import CompanySerializer
from base.views.base import CompanyFilterMixin
from base.tasks import celery_send_mail
from sales.models import Invoice, PaymentHistory, LeadDetail, CreditMemo, InvoiceTemplate
from sales.models.invoice import TemplateInvoice
from sales.models.proposal import ProposalWriting
from sales.serializers.invoice import InvoiceSerializer, InvoiceTemplateMinorSerializer, PaymentHistorySerializer, InvoicePaymentSerializer, \
    ProposalForInvoiceSerializer, LeadInvoiceSerializer, CreditMemoSerializer, InvoiceTemplateSerializer
from sales.views.lead_list import LeadDetailList
from sales.views.proposal import ProposalWritingCompactList
from sales.filters.invoice import InvoiceFilter


class InvoiceListView(CompanyFilterMixin, generics.ListCreateAPIView):
    queryset = Invoice.objects.all()
    serializer_class = InvoiceSerializer
    permission_classes = [permissions.IsAuthenticated & InvoicePermissions]
    filter_backends = (filters.DjangoFilterBackend, rf_filters.SearchFilter)
    filterset_class = InvoiceFilter
    search_fields = ('name',)


class InvoicePaymentListView(CompanyFilterMixin, generics.ListAPIView):
    queryset = Invoice.objects.all()
    serializer_class = InvoicePaymentSerializer
    permission_classes = [permissions.IsAuthenticated & InvoicePermissions]


class InvoiceDetailGenericView(CompanyFilterMixin, generics.RetrieveUpdateDestroyAPIView):
    queryset = Invoice.objects.all()
    serializer_class = InvoiceSerializer
    permission_classes = [permissions.IsAuthenticated & InvoicePermissions]


class InvoiceProposal(ProposalWritingCompactList):
    serializer_class = ProposalForInvoiceSerializer


class InvoiceProposalDetail(generics.RetrieveAPIView):
    serializer_class = ProposalForInvoiceSerializer
    queryset = ProposalWriting.objects.all().order_by('-modified_date')
    permission_classes = [permissions.IsAuthenticated & InvoicePermissions]

class PaymentListView(CompanyFilterMixin, generics.ListCreateAPIView):
    queryset = PaymentHistory.objects.all()
    serializer_class = PaymentHistorySerializer
    permission_classes = [permissions.IsAuthenticated & InvoicePermissions]


class PaymentDetailView(CompanyFilterMixin, generics.RetrieveUpdateDestroyAPIView):
    queryset = PaymentHistory.objects.all()
    serializer_class = PaymentHistorySerializer
    permission_classes = [permissions.IsAuthenticated & InvoicePermissions]


class LeadInvoiceList(LeadDetailList):
    serializer_class = LeadInvoiceSerializer
    permission_classes = [permissions.IsAuthenticated & InvoicePermissions]
    queryset = LeadDetail.objects.all()


class CreditMemoList(CompanyFilterMixin, generics.ListCreateAPIView):
    serializer_class = CreditMemoSerializer
    permission_classes = [permissions.IsAuthenticated & InvoicePermissions]
    queryset = CreditMemo.objects.all()


class CreditMemoDetail(CompanyFilterMixin, generics.RetrieveUpdateDestroyAPIView):
    serializer_class = CreditMemoSerializer
    permission_classes = [permissions.IsAuthenticated & InvoicePermissions]
    queryset = CreditMemo.objects.all()


class InvoiceTemplateList(CompanyFilterMixin, generics.ListCreateAPIView):
    serializer_class = InvoiceTemplateSerializer
    permission_classes = [permissions.IsAuthenticated & InvoicePermissions]
    queryset = InvoiceTemplate.objects.all()


class InvoiceTemplateDetail(CompanyFilterMixin, generics.RetrieveUpdateDestroyAPIView):
    serializer_class = InvoiceTemplateSerializer
    permission_classes = [permissions.IsAuthenticated & InvoicePermissions]
    queryset = InvoiceTemplate.objects.all()


@api_view(['GET', 'POST'])
def invoice_template_data(request, pk):
    invoice_obj = get_object_or_404(Invoice.objects.all(), pk=pk)
    template_obj = TemplateInvoice.objects.get_or_create(invoice=invoice_obj)[0]
    serializer = InvoiceTemplateMinorSerializer(template_obj)
    if request.method == 'POST':
        serializer = InvoiceTemplateMinorSerializer(instance=template_obj, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
    company = invoice_obj.company
    company_data = CompanySerializer(company).data
    data = {
        'items': [{'name': 'name', 'description': 'description',
                   'quantity': 'quantity', 'total_price': '100', 'unit_price': '123'} for i in range(5)],
        'company': company_data,
        'invoice': InvoiceSerializer(invoice_obj).data
    }
    return Response(status=status.HTTP_201_CREATED, data={**data, **serializer.data})


Contact = apps.get_model('sales', 'Contact')


@api_view(['POST'])
def publish_template(request):
    primary_contact = request.data['primary_contact']
    contacts = Contact.objects.get(pk__in=request.data['contacts'])
    for contact in contacts:
        url = f'{settings.BASE_URL}{request.data["path"]}'
        # if contact.pk == proposal_writing.proposal_formatting.primary_contact:
        #     url = url + f'?email={request.data["email"]}'
        content = render_to_string('proposal-formatting-sign.html', {'url': url, 'contact': contact})
        celery_send_mail.delay(f'Sign Electronically', content, settings.EMAIL_HOST_USER, [contact.email], False, html_message=content)
    return Response(status=status.HTTP_201_CREATED, data={'data': 'public success'})
