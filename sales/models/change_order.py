from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.utils import timezone

from api.models import BaseModel
from base.constants import DECIMAL_PLACE, MAX_DIGIT
from sales.models import Assemble, POFormula


class GroupEstimate(BaseModel):
    name = models.CharField(max_length=128, blank=True)
    order = models.IntegerField(blank=True, default=0)
    estimate_templates = models.ManyToManyField('sales.EstimateTemplate', blank=True, symmetrical=False,
                                                related_name='change_order_group')
    change_order = models.ForeignKey('sales.ChangeOrder', on_delete=models.CASCADE, blank=True, null=True,
                                     related_name='groups')


class GroupFlatRate(BaseModel):
    name = models.CharField(max_length=128, blank=True)
    change_order = models.ForeignKey('sales.ChangeOrder', on_delete=models.CASCADE,
                                     blank=True, null=True, related_name='flat_rate_groups')
    order = models.IntegerField(default=0, blank=True)


class FlatRate(BaseModel):
    name = models.CharField(max_length=128, default='')
    material_value = models.JSONField(blank=True, default=dict)
    copies_from = ArrayField(models.JSONField(blank=True, default=dict, null=True), default=list, blank=True, null=True)
    group = models.ForeignKey('sales.GroupFlatRate', on_delete=models.CASCADE,
                              blank=True, null=True, related_name='flat_rates')
    catalog_materials = ArrayField(models.JSONField(blank=True, default=dict, null=True), default=list, blank=True,
                                   null=True)
    quantity = models.IntegerField(default=0, blank=True)
    cost = models.DecimalField(default=0, blank=True, decimal_places=DECIMAL_PLACE, max_digits=MAX_DIGIT)
    charge = models.DecimalField(default=0, blank=True, decimal_places=DECIMAL_PLACE, max_digits=MAX_DIGIT)
    markup = models.DecimalField(default=0, blank=True, decimal_places=DECIMAL_PLACE, max_digits=MAX_DIGIT)
    unit = models.CharField(default='', blank=True, max_length=64)
    order = models.IntegerField(default=0, blank=True)


class ChangeOrder(BaseModel):
    name = models.CharField(max_length=128)
    approval_deadline = models.DateTimeField(default=timezone.now)
    owner_last_view = models.DateTimeField(auto_now=True, blank=True)
    proposal_writing = models.ForeignKey('sales.ProposalWriting', null=True, blank=True,
                                         on_delete=models.CASCADE, related_name='change_orders')
    existing_estimates = models.ManyToManyField('sales.EstimateTemplate', blank=True,
                                                related_name='change_order', symmetrical=False)

    def _get_formulas(self):
        estimate_templates = self.existing_estimates.all()
        for group in self.groups.all():
            estimate_templates |= group.estimate_templates.all()
        assembles = Assemble.objects.none()
        for estimate in estimate_templates:
            assembles |= estimate.assembles.all()
        poformulas = POFormula.objects.none()
        for assemble in assembles:
            poformulas |= assemble.assemble_formulas.all()
        return poformulas

    def _get_flat_rate(self):
        flat_rates = FlatRate.objects.none()
        for group in self.flat_rate_groups.all():
            flat_rates |= group.flat_rates.all()
        return flat_rates

    def get_items(self):
        items = self._get_changed_item() | self._get_new_items()
        return items


class ChangeOrderTemplate(BaseModel):
    change_order = models.OneToOneField('sales.ChangeOrder', on_delete=models.CASCADE,
                                        blank=True, null=True, related_name='templates')
    show_writing_fields = ArrayField(models.CharField(blank=True, max_length=128), default=list, blank=True)
    show_estimate_fields = ArrayField(models.CharField(blank=True, max_length=128), default=list, blank=True)
    show_format_fields = ArrayField(models.CharField(blank=True, max_length=128), default=list, blank=True)
    show_formula_fields = ArrayField(models.CharField(blank=True, max_length=128), default=list, blank=True)
    has_send_mail = models.BooleanField(default=False, blank=True)
    has_signed = models.BooleanField(default=False, blank=True)
    element = models.TextField(blank=True, null=True, default='')
    html_view = models.TextField(blank=True, null=True, default='')
    contacts = ArrayField(models.IntegerField(blank=True, null=True, default=None), default=list, blank=True, null=True)
    print_date = models.DateTimeField(default=None, blank=True, null=True)
    intro = models.TextField(blank=True)
    default_note = models.TextField(blank=True)
    pdf_file = models.CharField(max_length=128, blank=True)
    primary_contact = models.IntegerField(blank=True, null=True, default=None)
    otp = models.CharField(max_length=8, blank=True, default='', null=True)
    signature = models.CharField(max_length=256, blank=True, default='')
    sign_date = models.DateTimeField(default=None, blank=True, null=True)
    template_type = models.CharField(max_length=128, blank=True, default='')
