from rest_framework import generics, permissions

from api.models import ChangeOrderSetting
from api.serializers.base import ChangeOrderSettingSerializer
from base.views.base import CompanyFilterMixin


class ChangeOrderSettingGenericView(CompanyFilterMixin, generics.ListCreateAPIView):
    queryset = ChangeOrderSetting.objects.all()
    serializer_class = ChangeOrderSettingSerializer
    permission_classes = [permissions.IsAuthenticated]


class ChangeOrderSettingGenericViewDetailGenericView(CompanyFilterMixin, generics.RetrieveUpdateDestroyAPIView):
    queryset = ChangeOrderSetting.objects.all()
    serializer_class = ChangeOrderSettingSerializer
    permission_classes = [permissions.IsAuthenticated]