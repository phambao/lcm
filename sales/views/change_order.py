from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework import filters as rf_filters
from django_filters import rest_framework as filters

from base.permissions import ChangeOrderPermissions
from base.views.base import CompanyFilterMixin
from sales.models import ChangeOrder, ProposalWriting, POFormula
from sales.serializers import change_order
from sales.serializers.estimate import POFormulaDataSerializer
from sales.filters.change_order import ChangeOrderFilter


class ChangeOderList(CompanyFilterMixin, generics.ListCreateAPIView):
    queryset = ChangeOrder.objects.all().prefetch_related('existing_estimates', 'flat_rate_groups', 'groups').order_by('-modified_date')
    serializer_class = change_order.ChangeOrderSerializer
    permission_classes = [permissions.IsAuthenticated & ChangeOrderPermissions]
    filter_backends = (filters.DjangoFilterBackend, rf_filters.SearchFilter)
    filterset_class = ChangeOrderFilter
    search_fields = ('name',)


class ChangeOderListCompact(CompanyFilterMixin, generics.ListCreateAPIView):
    queryset = ChangeOrder.objects.all().select_related('proposal_writing')
    serializer_class = change_order.ChangeOrderSerializerCompact
    permission_classes = [permissions.IsAuthenticated & ChangeOrderPermissions]
    filter_backends = (filters.DjangoFilterBackend, rf_filters.SearchFilter)
    filterset_class = ChangeOrderFilter
    search_fields = ('name',)


class ChangeOderDetail(CompanyFilterMixin, generics.RetrieveUpdateDestroyAPIView):
    queryset = ChangeOrder.objects.all()
    serializer_class = change_order.ChangeOrderSerializer
    permission_classes = [permissions.IsAuthenticated & ChangeOrderPermissions]


class ChangeOrderFromProposalWritingList(generics.ListAPIView):
    queryset = ProposalWriting.objects.all()
    serializer_class = change_order.ChangeOrderForInvoice
    permission_classes = [permissions.IsAuthenticated & ChangeOrderPermissions]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return ProposalWriting.objects.none()
        proposal = get_object_or_404(ProposalWriting.objects.all(), pk=self.kwargs.get('pk'))
        change_orders = proposal.change_orders.all()
        return change_orders


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated & ChangeOrderPermissions])
def get_items(request, pk):
    cd = get_object_or_404(ChangeOrder.objects.all(), pk=pk)
    po_formulas = POFormula.objects.filter(company=request.user.company)[:20]
    data = POFormulaDataSerializer(po_formulas, context={'request': request}, many=True).data

    return Response(status=status.HTTP_200_OK, data=data)
