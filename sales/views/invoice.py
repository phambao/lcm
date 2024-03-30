from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions
from rest_framework import status, filters as rf_filters
from rest_framework.response import Response
from rest_framework.decorators import api_view
from django_filters import rest_framework as filters

from base.permissions import InvoicePermissions
from base.serializers.config import CompanySerializer
from base.views.base import CompanyFilterMixin
from sales.models import Invoice, PaymentHistory, LeadDetail, CreditMemo, InvoiceTemplate
from sales.models.proposal import ProposalWriting
from sales.serializers.invoice import InvoiceSerializer, PaymentHistorySerializer, InvoicePaymentSerializer, \
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


@api_view(['GET'])
def invoice_template_data(request, pk):
    invoice_obj = get_object_or_404(Invoice.objects.all(), pk=pk)
    company = invoice_obj.company
    company_data = CompanySerializer(company).data
    data = {
        'items': [{'name': 'name', 'description': 'description',
                   'quantity': 'quantity', 'total_price': '100', 'unit_price': '123'} for i in range(5)],
        'company': company_data,
        'invoice': InvoiceSerializer(invoice_obj).data
    }
    return Response(status=status.HTTP_201_CREATED, data=data)
