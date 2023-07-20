from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.utils import timezone

from api.models import BaseModel
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
    cost = models.DecimalField(default=0, blank=True, decimal_places=2, max_digits=16)
    charge = models.DecimalField(default=0, blank=True, decimal_places=2, max_digits=16)
    markup = models.DecimalField(default=0, blank=True, decimal_places=2, max_digits=16)
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
        assembles = Assemble.objects.none()
        for estimate in estimate_templates:
            assembles |= estimate.assembles.all()
        poformulas = POFormula.objects.none()
        for assemble in assembles:
            poformulas |= assemble.assemble_formulas.all()
        return poformulas

    def get_column_formula(self):
        return ['name', 'linked_description', 'formula', 'quantity', 'markup', 'charge', 'material', 'unit',
                'unit_price', 'cost', 'total_cost', 'gross_profit', 'description_of_formula', 'formula_scenario',
                'material_data_entry', 'formula_for_data_view', 'order']

    def _get_changed_item(self):
        if self.proposal_writing:
            changed_formulas = self._get_formulas().values(*self.get_column_formula())
            orginal_formula = self.proposal_writing.get_data_formula().values(*self.get_column_formula())
            diff_formula = []
            for changed_formula in changed_formulas:
                if changed_formula not in orginal_formula:
                    diff_formula.append(changed_formula)
            return diff_formula
        return None

    def _get_new_items(self):
        pass

    def get_items(self):
        items = self._get_changed_item() | self._get_new_items()
        return items
