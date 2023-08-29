from rest_framework import generics, permissions

from base.permissions import InvoicePermissions
from base.views.base import CompanyFilterMixin
from sales.models import Invoice, PaymentHistory, LeadDetail, CreditMemo
from sales.serializers.invoice import InvoiceSerializer, PaymentHistorySerializer, InvoicePaymentSerializer, \
    ProposalForInvoiceSerializer, LeadInvoiceSerializer, CreditMemoSerializer
from sales.views.lead_list import LeadDetailList
from sales.views.proposal import ProposalWritingCompactList


class InvoiceListView(CompanyFilterMixin, generics.ListCreateAPIView):
    queryset = Invoice.objects.all()
    serializer_class = InvoiceSerializer
    permission_classes = [permissions.IsAuthenticated & InvoicePermissions]


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


class CreditMemoDetail(CompanyFilterMixin, generics.ListCreateAPIView):
    serializer_class = CreditMemoSerializer
    permission_classes = [permissions.IsAuthenticated & InvoicePermissions]
    queryset = CreditMemo.objects.all()
