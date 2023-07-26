from rest_framework import serializers

from api.serializers.base import SerializerMixin
from base.utils import pop
from .lead_schedule import EventForInvoiceSerializer
from ..models.invoice import Invoice, TableInvoice, PaymentHistory


class PaymentHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentHistory
        fields = ('id', 'date', 'amount', 'payment_method', 'received_by')


class TableInvoiceSerializer(serializers.ModelSerializer, SerializerMixin):

    class Meta:
        model = TableInvoice
        fields = ('id', 'type', 'change_order', 'progress_payment', 'custom', 'proposal_items')

    def create(self, validated_data):
        instance = super().create(validated_data)
        return instance

    def update(self, instance, validated_data):
        instance = super().update(instance, validated_data)
        return instance

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if self.is_param_exist('pk'):
            pass
        return data


class InvoiceSerializer(serializers.ModelSerializer, SerializerMixin):
    tables = TableInvoiceSerializer('invoice', many=True, required=False, allow_null=True)
    payment_histories = PaymentHistorySerializer('invoice', many=True, required=False, allow_null=True)

    class Meta:
        model = Invoice
        fields = ('id', 'name', 'tables', 'date_paid', 'status', 'deadline', 'deadline_date',
                  'deadline_time', 'comment', 'note', 'proposal', 'payment_histories', 'link_to_event')

    def create_talbes(self, instance, tables):
        for table in tables:
            serializer = TableInvoiceSerializer(data=table, context=self.context)
            serializer.is_valid(raise_exception=True)
            obj = serializer.save(invoice=instance)

    def create_payment_history(self, instance, payment_histories):
        for ph in payment_histories:
            user = pop(ph, 'received_by', None)
            serializer = PaymentHistorySerializer(data=ph, context=self.context)
            serializer.is_valid(raise_exception=True)
            obj = serializer.save(invoice=instance, received_by=user)

    def create(self, validated_data):
        tables = pop(validated_data, 'tables', [])
        payment_histories = pop(validated_data, 'payment_histories', [])
        instance = super().create(validated_data)
        self.create_talbes(instance, tables)
        self.create_payment_history(instance, payment_histories)
        return instance

    def update(self, instance, validated_data):
        tables = pop(validated_data, 'tables', [])
        payment_histories = pop(validated_data, 'payment_histories', [])
        instance = super().update(instance, validated_data)
        instance.tables.all().delete()
        instance.payment_histories.all().delete()
        self.create_talbes(instance, tables)
        self.create_payment_history(instance, payment_histories)
        return instance

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if self.is_param_exist('pk'):
            # if instance.proposal:
            #     data['proposal'] = ProposalWritingSerializer(instance.proposal).data
            if instance.link_to_event:
                data['link_to_event'] = EventForInvoiceSerializer(instance.link_to_event).data
        return data
