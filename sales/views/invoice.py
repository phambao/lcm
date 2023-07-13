from rest_framework import generics, permissions

from base.views.base import CompanyFilterMixin
from sales.models import Invoice
from sales.serializers.invoice import InvoiceSerializer
from sales.views.proposal import ProposalWritingCompactList


class InvoiceListView(CompanyFilterMixin, generics.ListCreateAPIView):
    queryset = Invoice.objects.all()
    serializer_class = InvoiceSerializer
    permission_classes = [permissions.IsAuthenticated]


class InvoiceDetailGenericView(CompanyFilterMixin, generics.RetrieveUpdateDestroyAPIView):
    queryset = Invoice.objects.all()
    serializer_class = InvoiceSerializer
    permission_classes = [permissions.IsAuthenticated]


class InvoiceProposal(ProposalWritingCompactList):
    pass
