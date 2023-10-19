from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from api.models import ChangeOrderSetting, InvoiceSetting
from api.serializers.base import ChangeOrderSettingSerializer, InvoiceSettingSerializer


@api_view(['GET', 'PUT'])
@permission_classes([permissions.IsAuthenticated])
def setting_change_order(request):
    if request.method == 'GET':
        try:
            change_order_setting = ChangeOrderSetting.objects.get(company=request.user.company)
        except ChangeOrderSetting.DoesNotExist:
            change_order_setting = ChangeOrderSetting.objects.create(
                company=request.user.company,
                require_signature='ALL',
                change_order_approval='default change order approval',
                default_change_order="default change order"
            )

        serializer = ChangeOrderSettingSerializer(change_order_setting)
        return Response(status=status.HTTP_200_OK, data=serializer.data)

    if request.method == 'PUT':
        serializer = ChangeOrderSettingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data_insert = dict(serializer.validated_data)
        change_order_setting = ChangeOrderSetting.objects.get(company=request.user.company)
        change_order_setting.require_signature = data_insert['require_signature']
        change_order_setting.change_order_approval = data_insert['change_order_approval']
        change_order_setting.default_change_order = data_insert['default_change_order']
        change_order_setting.save()
        change_order_setting.refresh_from_db()
        serializer = ChangeOrderSettingSerializer(change_order_setting)
        return Response(status=status.HTTP_200_OK, data=serializer.data)
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['GET', 'PUT'])
@permission_classes([permissions.IsAuthenticated])
def setting_invoice(request):
    if request.method == 'GET':
        try:
            invoice_setting = InvoiceSetting.objects.get(company=request.user.company)
        except InvoiceSetting.DoesNotExist:
            invoice_setting = InvoiceSetting.objects.create(
                company=request.user.company,
                prefix='LCM',
                is_notify_internal_deadline=False,
                is_notify_owners_deadline=False,
                is_notify_owners_after_deadline=False,
                is_default_show=False,
                day_before=1,
                default_owners_invoice="default_owners_invoice"
            )

        serializer = InvoiceSettingSerializer(invoice_setting)
        return Response(status=status.HTTP_200_OK, data=serializer.data)

    if request.method == 'PUT':
        invoice_setting = InvoiceSetting.objects.get(company=request.user.company)
        serializer = InvoiceSettingSerializer(instance=invoice_setting, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_200_OK, data=serializer.data)
    return Response(status=status.HTTP_204_NO_CONTENT)
