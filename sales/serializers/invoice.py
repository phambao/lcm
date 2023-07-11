from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from base.utils import pop
from .change_order import ChangeOrderSerializer
from api.serializers.base import SerializerMixin
from .proposal import ProposalWritingSerializer
from ..models import ChangeOrder
from ..models.invoice import Invoice, TableInvoice


class TableInvoiceSerializer(serializers.ModelSerializer, SerializerMixin):
    class Meta:
        model = TableInvoice
        fields = ('id', 'type', 'change_orders')

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if self.is_param_exist('pk'):
            data['change_orders'] = ChangeOrderSerializer(ChangeOrder.objects.filter(pk__in=instance.change_orders), many=True).data
        return data


class InvoiceSerializer(serializers.ModelSerializer, SerializerMixin):
    tables = TableInvoiceSerializer('invoice', many=True, required=False, allow_null=True)

    class Meta:
        model = Invoice
        fields = ('id', 'name', 'tables', 'date_paid', 'status', 'deadline', 'deadline_date',
                  'deadline_time', 'comment', 'note', 'proposal')

    def create_talbes(self, instance, tables):
        for table in tables:
            serializer = TableInvoiceSerializer(data=table, context=self.context)
            serializer.is_valid(raise_exception=True)
            obj = serializer.save(invoice=instance)

    def create(self, validated_data):
        tables = pop(validated_data, 'tables', [])
        instance = super().create(validated_data)
        self.create_talbes(instance, tables)
        return instance

    def update(self, instance, validated_data):
        tables = pop(validated_data, 'tables', [])
        instance = super().update(instance, validated_data)
        instance.tables.all().delete()
        self.create_talbes(instance, tables)
        return instance

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if self.is_param_exist('pk'):
            if instance.proposal:
                data['proposal'] = ProposalWritingSerializer(instance.proposal).data
        return data