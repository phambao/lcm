from django.contrib.postgres.fields import ArrayField
from django.db import models

from api.models import BaseModel


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
    cost = models.DecimalField(default=0, blank=True, decimal_places=2, max_digits=16)
    charge = models.DecimalField(default=0, blank=True, decimal_places=2, max_digits=16)
    markup = models.DecimalField(default=0, blank=True, decimal_places=2, max_digits=16)
    unit = models.CharField(default='', blank=True, max_length=64)
    order = models.IntegerField(default=0, blank=True)


class ChangeOrder(BaseModel):
    name = models.CharField(max_length=128)
    proposal = models.ForeignKey('sales.ProposalFormatting', null=True, blank=True,
                                 on_delete=models.CASCADE, related_name='change_orders')
    existing_estimates = models.ManyToManyField('sales.EstimateTemplate', blank=True,
                                                related_name='change_order', symmetrical=False)
