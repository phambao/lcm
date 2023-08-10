from django.contrib.contenttypes.models import ContentType
from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from api.models import ActivityLog, Action
from base.permissions import InvoicePermissions
from base.views.base import CompanyFilterMixin
from sales.models import Invoice, PaymentHistory
from sales.serializers.invoice import InvoiceSerializer, PaymentHistorySerializer, InvoicePaymentSerializer
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
    pass


class PaymentListView(CompanyFilterMixin, generics.ListCreateAPIView):
    queryset = PaymentHistory.objects.all()
    serializer_class = PaymentHistorySerializer
    permission_classes = [permissions.IsAuthenticated & InvoicePermissions]


class PaymentDetailView(CompanyFilterMixin, generics.RetrieveUpdateDestroyAPIView):
    queryset = PaymentHistory.objects.all()
    serializer_class = PaymentHistorySerializer
    permission_classes = [permissions.IsAuthenticated & InvoicePermissions]


@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated & InvoicePermissions])
def delete_invoices(request):
    ids = request.data
    objs = Invoice.objects.filter(pk__in=ids)
    for obj in objs:
        ActivityLog.objects.create(
            content_type=ContentType.objects.get_for_model(Invoice), content_object=obj,
            object_id=obj.pk, action=Action.DELETE, last_state=InvoiceSerializer(obj).data, next_state={}
        )
    objs.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)
