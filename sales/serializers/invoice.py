from django.contrib.contenttypes.models import ContentType
from rest_framework import serializers
from rest_framework.exceptions import MethodNotAllowed
from rest_framework.generics import get_object_or_404

from api.serializers.base import SerializerMixin
from base.utils import pop
from base.tasks import activity_log
from base.serializers import base
from sales.models.invoice import InvoiceTemplate, TemplateInvoice
from sales.serializers import ContentTypeSerializerMixin
from ..models import (Invoice, TableInvoice, PaymentHistory, CustomTable, GroupChangeOrder, ChangeOrderItem,
                      ProposalWriting, ProposalItem, GroupProposal, ProgressPayment, LeadDetail, CreditMemoAmount,
                      CreditMemo, AttachmentInvoice, InvoiceTemplate)


class UnitSerializerMixin:
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['unit'] = 'USD'
        return data


class PaymentHistorySerializer(ContentTypeSerializerMixin, SerializerMixin):
    class Meta:
        model = PaymentHistory
        fields = ('id', 'date', 'amount', 'payment_method', 'received_by', 'status')

    def create(self, validated_data):
        invoice = get_object_or_404(Invoice.objects.all(), pk=self.get_params()['pk'])
        validated_data['invoice'] = invoice
        return super().create(validated_data)


class ProposalItemSerializer(UnitSerializerMixin, serializers.ModelSerializer):

    class Meta:
        model = ProposalItem
        fields = ('id', 'type', 'owner_price', 'amount_paid', 'unit', 'formula', 'percentage_payment')


class InvoiceTemplateMinorSerializer(serializers.ModelSerializer):

    class Meta:
        model = TemplateInvoice
        fields = ('id', 'description', 'printed', 'primary_contact', 'contacts')


class GroupProposalSerializer(UnitSerializerMixin, serializers.ModelSerializer):
    items = ProposalItemSerializer('group_proposal', many=True, allow_null=True, required=False)

    class Meta:
        model = GroupProposal
        fields = ('id', 'name', 'cost_type', 'percentage_payment', 'total_amount', 'quantity', 'proposal',
                  'unit', 'invoice_amount', 'items', 'is_formula')

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


class ProgressPaymentSerializer(UnitSerializerMixin, serializers.ModelSerializer):

    class Meta:
        model = ProgressPayment
        fields = ('id', 'name', 'cost_type', 'percentage_payment', 'total_amount', 'quantity',
                  'unit', 'invoice_amount')


class ChangeOrderItemSerializer(UnitSerializerMixin, serializers.ModelSerializer):

    class Meta:
        model = ChangeOrderItem
        fields = ('id', 'type', 'owner_price', 'amount_paid', 'unit', 'formula', 'percentage_payment')


class GroupChangeOrderSerializer(UnitSerializerMixin, serializers.ModelSerializer):
    groups = ChangeOrderItemSerializer('group_change_order', many=True, allow_null=True, required=False)

    class Meta:
        model = GroupChangeOrder
        fields = ('id', 'name', 'cost_type', 'percentage_payment', 'total_amount', 'quantity', 'change_order',
                  'unit', 'invoice_amount', 'groups', 'is_formula')

    def create_change_order_items(self, items, instance):
        for item in items:
            serializer = ChangeOrderItemSerializer(data=item, context=self.context)
            serializer.is_valid(raise_exception=True)
            serializer.save(group_change_order=instance)

    def create(self, validated_data):
        items = pop(validated_data, 'groups', [])
        instance = super().create(validated_data)
        self.create_change_order_items(items, instance)
        return instance

    def update(self, instance, validated_data):
        items = pop(validated_data, 'groups', [])
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
    progress_payments = ProgressPaymentSerializer('table_invoice', many=True, allow_null=True, required=False)

    class Meta:
        model = TableInvoice
        fields = ('id', 'type', 'progress_payments', 'customs', 'group_change_orders', 'group_proposal')

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

    def create_progress_payment(self, progress_payments, instance):
        for progress_payment in progress_payments:
            serializer = ProgressPaymentSerializer(data=progress_payment, context=self.context)
            serializer.is_valid(raise_exception=True)
            serializer.save(table_invoice=instance)

    def create(self, validated_data):
        customs = pop(validated_data, 'customs', [])
        group_change_orders = pop(validated_data, 'group_change_orders', [])
        group_proposal = pop(validated_data, 'group_proposal', [])
        progress_payment = pop(validated_data, 'progress_payments', [])
        instance = super().create(validated_data)
        self.create_custom_table(customs, instance)
        self.create_group_change_orders(group_change_orders, instance)
        self.create_group_proposal(group_proposal, instance)
        self.create_progress_payment(progress_payment, instance)
        return instance

    def update(self, instance, validated_data):
        customs = pop(validated_data, 'customs', [])
        group_change_orders = pop(validated_data, 'group_change_orders', [])
        group_proposal = pop(validated_data, 'group_proposal', [])
        progress_payment = pop(validated_data, 'progress_payments', [])
        instance = super().update(instance, validated_data)
        instance.customs.all().delete()
        instance.group_change_orders.all().delete()
        instance.group_proposal.all().delete()
        instance.progress_payments.all().delete()
        self.create_group_change_orders(group_change_orders, instance)
        self.create_custom_table(customs, instance)
        self.create_group_proposal(group_proposal, instance)
        self.create_progress_payment(progress_payment, instance)
        return instance

    def to_representation(self, instance):
        data = super().to_representation(instance)
        return data


class AttachmentInvoiceSerializer(serializers.ModelSerializer, SerializerMixin):
    class Meta:
        model = AttachmentInvoice
        fields = ('file', 'name', 'size')


class InvoiceSerializer(ContentTypeSerializerMixin, SerializerMixin):
    tables = TableInvoiceSerializer('invoice', many=True, required=False, allow_null=True)
    payment_histories = PaymentHistorySerializer('invoice', many=True, required=False, allow_null=True)
    attachments = AttachmentInvoiceSerializer(many=True, required=False, allow_null=True)

    class Meta:
        model = Invoice
        fields = ('id', 'name', 'tables', 'date_paid', 'status', 'deadline', 'attachments', 'deadline_datetime',
                  'comment', 'note', 'proposal', 'link_to_event', 'payment_histories', 'created_date', 'owner_note',)
        read_only_fields = ('created_date', )

    def create_attachment(self, instance, attachments):
        for attachment in attachments:
            serializer = AttachmentInvoiceSerializer(data=attachment, context=self.context)
            serializer.is_valid(raise_exception=True)
            obj = serializer.save(content_object=instance)

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
        attachments = pop(validated_data, 'attachments', [])
        instance = super().create(validated_data)
        self.create_talbes(instance, tables)
        # self.create_payment_history(instance, payment_histories)
        self.create_attachment(instance, attachments)
        activity_log.delay(instance.get_content_type().pk, instance.pk, 1,
                           InvoiceSerializer.__name__, __name__, self.context['request'].user.pk)
        return instance

    def update(self, instance, validated_data):
        tables = pop(validated_data, 'tables', [])
        payment_histories = pop(validated_data, 'payment_histories', [])
        attachments = pop(validated_data, 'attachments', [])
        instance = super().update(instance, validated_data)
        instance.tables.all().delete()
        # instance.payment_histories.all().delete()
        AttachmentInvoice.objects.filter(content_type=ContentType.objects.get_for_model(instance),
                                         object_id=instance.id).delete()
        self.create_talbes(instance, tables)
        # self.create_payment_history(instance, payment_histories)
        self.create_attachment(instance, attachments)
        activity_log.delay(instance.get_content_type().pk, instance.pk, 2,
                           InvoiceSerializer.__name__, __name__, self.context['request'].user.pk)
        return instance

    def to_representation(self, instance):
        data = super().to_representation(instance)
        attachments = AttachmentInvoice.objects.filter(content_type=ContentType.objects.get_for_model(instance),
                                                       object_id=instance.id)
        attachment_data = AttachmentInvoiceSerializer(attachments, many=True).data
        data['attachments'] = attachment_data
        data['lead_name'] = ''
        data['lead_id'] = None
        if instance.proposal:
            if instance.proposal.lead:
                data['lead_name'] = instance.proposal.lead.lead_title
                data['lead_id'] = instance.proposal.lead.id
        # if instance.link_to_event:
        #     data['link_to_event'] = EventForInvoiceSerializer(instance.link_to_event).data
        return data


class InvoicePaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invoice
        fields = ('id', 'name')

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['payments'] = PaymentHistorySerializer(instance.payment_histories.all(), many=True, context=self.context).data
        return data


class ProposalForInvoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProposalWriting
        fields = ('id', 'name', 'created_date', 'lead', 'total_project_price', 'total_project_cost', 'additional_information')

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['status'] = 'Approved'
        data['owner_price'] = instance.total_project_price
        return data


class LeadInvoiceSerializer(serializers.ModelSerializer):

    class Meta:
        model = LeadDetail
        fields = ('id', 'lead_title', 'country', 'city', 'state', 'street_address')

    def create(self, validated_data):
        raise MethodNotAllowed('POST')


class CreditMemoAmountSerializer(serializers.ModelSerializer):
    class Meta:
        model = CreditMemoAmount
        fields = ('id', 'name', 'cost_type', 'unit_amount', 'quantity', 'invoice_amount')


class CreditMemoSerializer(ContentTypeSerializerMixin):
    credit_memo_amounts = CreditMemoAmountSerializer('credit_memo', many=True, allow_null=True, required=False)
    attachments = AttachmentInvoiceSerializer(many=True, required=False, allow_null=True)

    class Meta:
        model = CreditMemo
        fields = ('id', 'name', 'description', 'credit_memo_amounts', 'attachments', 'invoice')

    def create_attachment(self, instance, attachments):
        for attachment in attachments:
            serializer = AttachmentInvoiceSerializer(data=attachment, context=self.context)
            serializer.is_valid(raise_exception=True)
            obj = serializer.save(content_object=instance)

    def create_memo_amount(self, instance, credit_memo_amounts):
        for credit_memo_amount in credit_memo_amounts:
            serializer = CreditMemoAmountSerializer(data=credit_memo_amount, context=self.context)
            serializer.is_valid(raise_exception=True)
            obj = serializer.save(credit_memo=instance)

    def create(self, validated_data):
        credit_memo_amounts = pop(validated_data, 'credit_memo_amounts', [])
        attachments = pop(validated_data, 'attachments', [])
        instance = super().create(validated_data)
        self.create_memo_amount(instance, credit_memo_amounts)
        self.create_attachment(instance, attachments)
        return instance

    def update(self, instance, validated_data):
        credit_memo_amounts = pop(validated_data, 'credit_memo_amounts', [])
        attachments = pop(validated_data, 'attachments', [])
        instance.credit_memo_amounts.all().delete()
        AttachmentInvoice.objects.filter(content_type=ContentType.objects.get_for_model(instance),
                                         object_id=instance.id).delete()
        self.create_memo_amount(instance, credit_memo_amounts)
        self.create_attachment(instance, attachments)
        return super().update(instance, validated_data)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        attachments = AttachmentInvoice.objects.filter(content_type=ContentType.objects.get_for_model(instance),
                                                       object_id=instance.id)
        attachment_data = AttachmentInvoiceSerializer(attachments, many=True).data
        data['attachments'] = attachment_data
        return data


class InvoiceTemplateSerializer(ContentTypeSerializerMixin):
    class Meta:
        model = InvoiceTemplate
        fields = ('id', 'name', 'description', 'created_date', 'user_create')
        read_only_fields = ('user_create', )

    def create(self, validated_data):
        instance = super().create(validated_data)
        activity_log.delay(instance.get_content_type().pk, instance.pk, 1,
                           InvoiceTemplateSerializer.__name__, __name__, self.context['request'].user.pk)
        return instance

    def update(self, instance, validated_data):
        activity_log.delay(instance.get_content_type().pk, instance.pk, 2,
                           InvoiceTemplateSerializer.__name__, __name__, self.context['request'].user.pk)
        return super().update(instance, validated_data)
