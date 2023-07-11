from rest_framework import generics, permissions
from rest_framework.generics import get_object_or_404

from base.views.base import CompanyFilterMixin
from sales.models import ChangeOrder, ProposalWriting
from sales.serializers import change_order


class ChangeOderList(CompanyFilterMixin, generics.ListCreateAPIView):
    queryset = ChangeOrder.objects.all().prefetch_related('existing_estimates', 'flat_rate_groups', 'groups')
    serializer_class = change_order.ChangeOrderSerializer
    permission_classes = [permissions.IsAuthenticated]


class ChangeOderDetail(CompanyFilterMixin, generics.RetrieveUpdateDestroyAPIView):
    queryset = ChangeOrder.objects.all()
    serializer_class = change_order.ChangeOrderSerializer
    permission_classes = [permissions.IsAuthenticated]


class ChangeOrderFromProposalWritingList(generics.ListAPIView):
    queryset = ProposalWriting.objects.all()
    serializer_class = change_order.ChangeOrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        proposal = get_object_or_404(ProposalWriting.objects.all(), pk=self.kwargs.get('pk'))
        change_orders = proposal.change_orders.all()
        return change_orders
