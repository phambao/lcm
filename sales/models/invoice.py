from django.contrib.auth import get_user_model
from django.db import models
from django.contrib.postgres.fields import ArrayField

from api.models import BaseModel


class TableInvoice(BaseModel):
    class TableTypeInvoice(models.TextChoices):
        CHANGE_ORDER = 'change_order', 'Change Order'
        PROGRESS_PAYMENT_FROM_PROPOSAL = 'progress_payment_from_proposal', 'Progress Payment From Proposal'
        PROPOSAL_ITEMS = 'proposal_items', 'Proposal Item'
        CUSTOM = 'custom', 'Custom'
    type = models.CharField(max_length=32, choices=TableTypeInvoice.choices, default=TableTypeInvoice.CHANGE_ORDER)
    change_orders = ArrayField(models.IntegerField(blank=True), default=list, blank=True)
    invoice = models.ForeignKey('sales.Invoice', blank=True, null=True, on_delete=models.CASCADE, related_name='tables')
    progress_payment = ArrayField(models.JSONField(blank=True, null=True), default=list, blank=True)


class PaymentHistory(BaseModel):
    invoice = models.ForeignKey('sales.Invoice', blank=True, null=True,
                                on_delete=models.CASCADE, related_name='payment_histories')
    date = models.DateField()
    amount = models.DecimalField(default=0, max_digits=32, decimal_places=2)
    unit_cost = models.CharField(max_length=32)
    received_by = models.ForeignKey(get_user_model(), on_delete=models.SET_NULL, related_name='payments',
                                    null=True, blank=True)


class Invoice(BaseModel):
    class InvoiceStatus(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        UNPAID = 'unpaid', 'Unpaid'
        PAID = 'paid', 'Paid'

    name = models.CharField(max_length=64)
    date_paid = models.DateTimeField()
    status = models.CharField(max_length=16, choices=InvoiceStatus.choices, default=InvoiceStatus.PAID)
    deadline = models.BooleanField(default=False)
    deadline_date = models.DateField(blank=True, null=True)
    deadline_time = models.TimeField(blank=True, null=True)
    comment = models.TextField(blank=True)
    note = models.TextField(blank=True)
    proposal = models.ForeignKey('sales.ProposalWriting', on_delete=models.CASCADE, related_name='invoices', blank=True, null=True)
