from rest_framework import serializers

from api.serializers.base import SerializerMixin
from base.utils import pop
from .lead_schedule import EventForInvoiceSerializer
from ..models.invoice import (Invoice, TableInvoice, PaymentHistory, CustomTable, GroupChangeOrder, ChangeOrderItem,
                              ProposalItem, GroupProposal)


class PaymentHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentHistory
        fields = ('id', 'date', 'amount', 'payment_method', 'received_by')


class ProposalItemSerializer(serializers.ModelSerializer):

    class Meta:
        model = ProposalItem
        fields = ('id', 'type', 'owner_price', 'amount_paid', 'unit', 'formula')


class GroupProposalSerializer(serializers.ModelSerializer):
    items = ProposalItemSerializer('group_proposal', many=True, allow_null=True, required=False)

    class Meta:
        model = GroupProposal
        fields = ('id', 'name', 'cost_type', 'percentage_payment', 'total_amount', 'quantity', 'proposal',
                  'unit', 'invoice_amount', 'items')

    def create_proposal_items(self, items, instance):
        for item in items:
            serializer = ProposalItemSerializer(data=item, context=self.context)
            serializer.is_valid(raise_exception=True)
            serializer.save(group_proposal=instance)

    def create(self, validated_data):
        items = pop(validated_data, 'items', [])
        instance = super().create(validated_data)
        self.create_proposal_items(items, instance)
        return instance

    def update(self, instance, validated_data):
        items = pop(validated_data, 'items', [])
        instance = super().update(instance, validated_data)
        instance.items.all().delete()
        self.create_proposal_items(items, instance)
        return instance


class ChangeOrderItemSerializer(serializers.ModelSerializer):

    class Meta:
        model = ChangeOrderItem
        fields = ('id', 'type', 'owner_price', 'amount_paid', 'unit', 'formula')


class GroupChangeOrderSerializer(serializers.ModelSerializer):
    items = ChangeOrderItemSerializer('group_change_order', many=True, allow_null=True, required=False)

    class Meta:
        model = GroupChangeOrder
        fields = ('id', 'name', 'cost_type', 'percentage_payment', 'total_amount', 'quantity', 'change_order',
                  'unit', 'invoice_amount', 'items')

    def create_change_order_items(self, items, instance):
        for item in items:
            serializer = ChangeOrderItemSerializer(data=item, context=self.context)
            serializer.is_valid(raise_exception=True)
            serializer.save(group_change_order=instance)

    def create(self, validated_data):
        items = pop(validated_data, 'items', [])
        instance = super().create(validated_data)
        self.create_change_order_items(items, instance)
        return instance

    def update(self, instance, validated_data):
        items = pop(validated_data, 'items', [])
        instance = super().update(instance, validated_data)
        instance.items.all().delete()
        self.create_change_order_items(items, instance)
        return instance


class CustomTableSerializer(serializers.ModelSerializer):

    class Meta:
        model = CustomTable
        fields = ('id', 'name', 'cost_type', 'unit_cost', 'quantity', 'unit')


class TableInvoiceSerializer(serializers.ModelSerializer, SerializerMixin):
    customs = CustomTableSerializer('table_invoice', many=True, allow_null=True, required=False)
    group_change_orders = GroupChangeOrderSerializer('table_invoice', many=True, allow_null=True, required=False)
    group_proposal = GroupProposalSerializer('table_invoice', many=True, allow_null=True, required=False)

    class Meta:
        model = TableInvoice
        fields = ('id', 'type', 'progress_payment', 'customs', 'group_change_orders', 'group_proposal')

    def create_custom_table(self, customs, instance):
        for custom in customs:
            serializer = CustomTableSerializer(data=custom, context=self.context)
            serializer.is_valid(raise_exception=True)
            serializer.save(table_invoice=instance)

    def create_group_change_orders(self, group_change_orders, instance):
        for group in group_change_orders:
            serializer = GroupChangeOrderSerializer(data=group, context=self.context)
            serializer.is_valid(raise_exception=True)
            serializer.save(table_invoice=instance)

    def create_group_proposal(self, group_proposals, instance):
        for group_proposal in group_proposals:
            serializer = GroupProposalSerializer(data=group_proposal, context=self.context)
            serializer.is_valid(raise_exception=True)
            serializer.save(table_invoice=instance)

    def create(self, validated_data):
        customs = pop(validated_data, 'customs', [])
        group_change_orders = pop(validated_data, 'group_change_orders', [])
        group_proposal = pop(validated_data, 'group_proposal', [])
        instance = super().create(validated_data)
        self.create_custom_table(customs, instance)
        self.create_group_change_orders(group_change_orders, instance)
        self.create_group_proposal(group_proposal, instance)
        return instance

    def update(self, instance, validated_data):
        customs = pop(validated_data, 'customs', [])
        group_change_orders = pop(validated_data, 'group_change_orders', [])
        group_proposal = pop(validated_data, 'group_proposal', [])
        instance = super().update(instance, validated_data)
        instance.customs.all().delete()
        instance.group_change_orders.all().delete()
        instance.group_proposal.all().delete()
        self.create_group_change_orders(group_change_orders, instance)
        self.create_custom_table(customs, instance)
        self.create_group_proposal(group_proposal, instance)
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
