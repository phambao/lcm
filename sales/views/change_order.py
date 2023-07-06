from django_filters import rest_framework as filters
from rest_framework import generics, permissions, status, filters as rf_filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from base.views.base import CompanyFilterMixin
from sales.models import ChangeOrder
from sales.serializers import change_order


class ChangeOderList(CompanyFilterMixin, generics.ListCreateAPIView):
    queryset = ChangeOrder.objects.all().prefetch_related('existing_estimates', 'flat_rate_groups', 'groups')
    serializer_class = change_order.ChangeOrderSerializer
    permission_classes = [permissions.IsAuthenticated]


class ChangeOderDetail(CompanyFilterMixin, generics.RetrieveUpdateDestroyAPIView):
    queryset = ChangeOrder.objects.all()
    serializer_class = change_order.ChangeOrderSerializer
    permission_classes = [permissions.IsAuthenticated]
