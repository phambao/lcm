from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.contrib.postgres.fields import ArrayField

from api.models import BaseModel
from base.constants import DECIMAL_PLACE, MAX_DIGIT


class TableInvoice(BaseModel):
    class TableTypeInvoice(models.TextChoices):
        CHANGE_ORDER = 'change_order', 'Change Order'
        PROGRESS_PAYMENT_FROM_PROPOSAL = 'progress_payment_from_proposal', 'Progress Payment From Proposal'
        PROPOSAL_ITEMS = 'proposal_items', 'Proposal Item'
        CUSTOM = 'custom', 'Custom'
    type = models.CharField(max_length=32, choices=TableTypeInvoice.choices, default=TableTypeInvoice.CHANGE_ORDER)
    invoice = models.ForeignKey('sales.Invoice', blank=True, null=True, on_delete=models.CASCADE, related_name='tables')


class PaymentHistory(BaseModel):
    class PaymentStatus(models.TextChoices):
        CREDIT_CARD = 'credit_card', 'Credit Card'
        CHECK = 'check', 'Check'
        OTHER = 'other', 'Other'
    class InvoiceStatus(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        SENT = 'sent', 'Sent'
        UNPAID = 'unpaid', 'Unpaid'
        PAID = 'paid', 'Paid'
    invoice = models.ForeignKey('sales.Invoice', blank=True, null=True,
                                on_delete=models.CASCADE, related_name='payment_histories')
    status = models.CharField(max_length=16, choices=InvoiceStatus.choices, default=InvoiceStatus.PAID)
    date = models.DateTimeField()
    amount = models.DecimalField(default=0, max_digits=MAX_DIGIT, decimal_places=DECIMAL_PLACE)
    payment_method = models.CharField(max_length=32, choices=PaymentStatus.choices, default=PaymentStatus.CREDIT_CARD)
    received_by = models.ForeignKey(get_user_model(), on_delete=models.SET_NULL, related_name='payments',
                                    null=True, blank=True)


class CustomTable(BaseModel):
    name = models.CharField(max_length=64)
    cost_type = models.CharField(max_length=64)
    unit_cost = models.DecimalField(max_digits=MAX_DIGIT, decimal_places=DECIMAL_PLACE)
    quantity = models.IntegerField()
    unit = models.CharField(max_length=64)
    table_invoice = models.ForeignKey('sales.TableInvoice', on_delete=models.CASCADE, blank=True, null=True, related_name='customs')


class GroupChangeOrder(BaseModel):
    table_invoice = models.ForeignKey('sales.TableInvoice', on_delete=models.CASCADE, blank=True, null=True,
                                      related_name='group_change_orders')
    change_order = models.IntegerField(blank=True, default=None, null=True)
    name = models.CharField(max_length=64)
    cost_type = models.CharField(max_length=128, blank=True, default='')
    percentage_payment = models.IntegerField(blank=True, default=100)
    total_amount = models.DecimalField(max_digits=MAX_DIGIT, decimal_places=DECIMAL_PLACE, default=0, blank=True)
    quantity = models.IntegerField(default=0, blank=True)
    unit = models.CharField(blank=True, default='', max_length=32)
    invoice_amount = models.DecimalField(max_digits=MAX_DIGIT, decimal_places=DECIMAL_PLACE, default=0, blank=True)
    is_formula = models.BooleanField(default=True, blank=True)


class ProgressPayment(BaseModel):
    table_invoice = models.OneToOneField('sales.TableInvoice', on_delete=models.CASCADE, blank=True, null=True,
                                         related_name='progress_payment')
    name = models.CharField(max_length=64)
    cost_type = models.CharField(max_length=128, blank=True, default='')
    percentage_payment = models.IntegerField(blank=True, default=100)
    total_amount = models.DecimalField(max_digits=MAX_DIGIT, decimal_places=DECIMAL_PLACE, default=0, blank=True)
    quantity = models.IntegerField(default=0, blank=True)
    unit = models.CharField(blank=True, default='', max_length=32)
    invoice_amount = models.DecimalField(max_digits=MAX_DIGIT, decimal_places=DECIMAL_PLACE, default=0, blank=True)
    items = ArrayField(models.JSONField(blank=True, null=True), default=list, blank=True)


class ChangeOrderItem(BaseModel):
    formula = models.IntegerField(blank=True, default=None, null=True)
    group_change_order = models.ForeignKey('sales.GroupChangeOrder', on_delete=models.CASCADE, blank=True, null=True,
                                           related_name='groups')
    type = models.CharField(max_length=128, blank=True, default='')
    owner_price = models.DecimalField(max_digits=MAX_DIGIT, decimal_places=DECIMAL_PLACE, default=0, blank=True)
    amount_paid = models.DecimalField(max_digits=MAX_DIGIT, decimal_places=DECIMAL_PLACE, default=0, blank=True)  # new invoice amount
    unit = models.CharField(blank=True, default='', max_length=32)
    percentage_payment = models.IntegerField(blank=True, default=100)


class GroupProposal(BaseModel):
    table_invoice = models.ForeignKey('sales.TableInvoice', on_delete=models.CASCADE, blank=True, null=True,
                                      related_name='group_proposal')
    proposal = models.IntegerField(blank=True, default=None, null=True)
    name = models.CharField(max_length=64)
    cost_type = models.CharField(max_length=128, blank=True, default='')
    percentage_payment = models.IntegerField(blank=True, default=100)
    total_amount = models.DecimalField(max_digits=MAX_DIGIT, decimal_places=DECIMAL_PLACE, default=0, blank=True)
    quantity = models.IntegerField(default=0, blank=True)
    unit = models.CharField(blank=True, default='', max_length=32)
    invoice_amount = models.DecimalField(max_digits=MAX_DIGIT, decimal_places=DECIMAL_PLACE, default=0, blank=True)
    is_formula = models.BooleanField(default=True, blank=True)


class ProposalItem(BaseModel):
    formula = models.IntegerField(blank=True, default=None, null=True)
    group_proposal = models.ForeignKey('sales.GroupProposal', on_delete=models.CASCADE, blank=True, null=True,
                                       related_name='items')
    type = models.CharField(max_length=128, blank=True, default='')
    owner_price = models.DecimalField(max_digits=MAX_DIGIT, decimal_places=DECIMAL_PLACE, default=0, blank=True)
    amount_paid = models.DecimalField(max_digits=MAX_DIGIT, decimal_places=DECIMAL_PLACE, default=0, blank=True)
    unit = models.CharField(blank=True, default='', max_length=32)
    percentage_payment = models.IntegerField(blank=True, default=100)


class Invoice(BaseModel):
    class Meta:
        permissions = [('create_edit_credit_memo', 'Can Create/Edit Credit Memo')]

    class InvoiceStatus(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        SENT = 'sent', 'Sent'
        UNPAID = 'unpaid', 'Unpaid'
        PAID = 'paid', 'Paid'

    name = models.CharField(max_length=64)
    date_paid = models.DateTimeField()
    status = models.CharField(max_length=16, choices=InvoiceStatus.choices, default=InvoiceStatus.PAID)
    deadline = models.BooleanField(default=False)
    deadline_datetime = models.DateTimeField(blank=True, null=True)
    link_to_event = models.ForeignKey('sales.ScheduleEvent', on_delete=models.CASCADE, related_name='invoice', blank=True, null=True)
    comment = models.TextField(blank=True)
    note = models.TextField(blank=True)
    proposal = models.ForeignKey('sales.ProposalWriting', on_delete=models.CASCADE, related_name='invoices', blank=True, null=True)

    def get_proposal(self):
        data = []
        proposal_items = GroupProposal.objects.filter(table_invoice__invoice=self)
        for item in proposal_items:
            quantity = item.quantity if item.quantity else 1
            unit_price = item.invoice_amount / quantity
            data.append({
                'name': item.name, 'description': '', 'quantity': quantity, 'unit_price': unit_price, 'total_price': item.invoice_amount
            })
        return data

    def get_change_order(self):
        change_order_items = GroupChangeOrder.objects.filter(table_invoice__invoice=self)
        data = []
        for item in change_order_items:
            quantity = item.quantity if item.quantity else 1
            unit_price = item.invoice_amount / quantity
            data.append({
                'name': item.name, 'description': '', 'quantity': quantity, 'unit_price': unit_price, 'total_price': item.invoice_amount
            })
        return data

    def get_progress(self):
        data = []
        progress = ProgressPayment.objects.filter(table_invoice__invoice=self)
        for item in progress:
            quantity = item.quantity if item.quantity else 1
            unit_price = item.invoice_amount / quantity
            data.append({
                'name': item.name, 'description': '', 'quantity': quantity, 'unit_price': unit_price, 'total_price': item.invoice_amount
            })
        return data

    def get_custom(self):
        data = []
        customs = CustomTable.objects.filter(table_invoice__invoice=self)
        for item in customs:
            quantity = item.quantity if item.quantity else 1
            total_price = item.unit_cost * quantity
            data.append({
                'name': item.name, 'description': '', 'quantity': quantity, 'unit_price': item.unit_cost, 'total_price': total_price
            })
        return data

    def get_items(self):
        data = []
        data.extend(self.get_change_order())
        data.extend(self.get_proposal())
        data.extend(self.get_custom())
        data.extend(self.get_progress())
        return data


class TemplateInvoice(BaseModel):
    invoice = models.OneToOneField(Invoice, on_delete=models.CASCADE, related_name='template', blank=True, null=True)
    description = models.TextField(blank=True)
    printed = models.DateTimeField(blank=True, null=True)
    primary_contact = models.IntegerField(blank=True, null=True, default=None)
    contacts = ArrayField(models.IntegerField(blank=True, null=True, default=None), default=list, blank=True, null=True)
    signature = models.CharField(max_length=256, blank=True, default='')
    otp = models.CharField(max_length=8, blank=True, default='', null=True)
    has_send_mail = models.BooleanField(default=False, blank=True)
    has_signed = models.BooleanField(default=False, blank=True)


class CreditMemoAmount(BaseModel):
    name = models.CharField(max_length=64)
    cost_type = models.CharField(max_length=64)
    unit_amount = models.DecimalField(max_digits=MAX_DIGIT, decimal_places=DECIMAL_PLACE, default=0, blank=True)
    quantity = models.IntegerField(blank=True, default=0, null=True)
    invoice_amount = models.DecimalField(max_digits=MAX_DIGIT, decimal_places=DECIMAL_PLACE, default=0, blank=True)
    credit_memo = models.ForeignKey('sales.CreditMemo', blank=True, null=True,
                                    related_name='credit_memo_amounts', on_delete=models.CASCADE)


class CreditMemo(BaseModel):
    name = models.CharField(max_length=64)
    description = models.TextField(blank=True, default='')
    invoice = models.ForeignKey('sales.Invoice', blank=True, null=True,
                                on_delete=models.CASCADE, related_name='credit_memos')


class AttachmentInvoice(BaseModel):
    file = models.CharField(max_length=128)
    name = models.CharField(max_length=128)
    size = models.IntegerField(blank=True, null=True)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    class Meta:
        db_table = 'attachment_invoice'
        indexes = [
            models.Index(fields=["content_type", "object_id"]),
        ]


class InvoiceTemplate(BaseModel):
    name = models.CharField(max_length=128)
    description = models.TextField(blank=True, default='')
