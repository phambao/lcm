from django.db import models
from django.contrib.postgres.fields import ArrayField

from api.models import BaseModel


class UnitLibrary(BaseModel):
    name = models.CharField(max_length=128)
    description = models.TextField(default='', blank=True)


class DataEntry(BaseModel):

    name = models.CharField(max_length=128)
    unit = models.ForeignKey('sales.UnitLibrary', on_delete=models.SET_NULL,
                             blank=True, null=True, related_name='data_entries')
    is_dropdown = models.BooleanField(default=False)
    dropdown = ArrayField(models.JSONField(blank=True, null=True), default=list, blank=True)


class POFormula(BaseModel):

    name = models.CharField(max_length=128)
    linked_description = models.TextField(blank=True, default='')
    show_color = models.BooleanField(default=False)
    formula = models.TextField()
    group = models.ForeignKey('sales.POFormulaGrouping', blank=True, related_name='group_formulas', null=True, on_delete=models.SET_NULL)
    assemble = models.ForeignKey('sales.Assemble', blank=True, related_name='assemble_formulas', null=True, on_delete=models.SET_NULL)
    related_formulas = models.ManyToManyField('self', related_name='used_by', symmetrical=False, blank=True)
    created_from = models.ForeignKey('self', related_name='clones', null=True, blank=True, on_delete=models.SET_NULL)
    is_show = models.BooleanField(default=True, blank=True)  # Only show formula page
    quantity = models.CharField(max_length=64, blank=True)
    markup = models.CharField(max_length=64, blank=True)
    charge = models.CharField(max_length=64, blank=True)
    material = models.CharField(max_length=32, blank=True)
    unit = models.CharField(max_length=32, blank=True)
    cost = models.IntegerField(blank=True, default=0)
    catalog_links = models.ManyToManyField('sales.Catalog', related_name='formulas', blank=True)
    formula_mentions = models.CharField(blank=True, max_length=256)
    gross_profit = models.CharField(max_length=32, blank=True)
    description_of_formula = models.TextField(blank=True)
    formula_scenario = models.TextField(blank=True)


class POFormulaToDataEntry(BaseModel):
    data_entry = models.ForeignKey(DataEntry, on_delete=models.CASCADE, blank=True, null=True)
    po_formula = models.ForeignKey(POFormula, on_delete=models.CASCADE, blank=True,
                                   null=True, related_name='self_data_entries')
    value = models.CharField(verbose_name='Default Value', max_length=32, blank=True)
    index = models.IntegerField(blank=True, default=0)
    dropdown_value = models.JSONField(blank=True, default=dict)


class POFormulaGrouping(BaseModel):
    name = models.CharField(max_length=128)


class Assemble(BaseModel):
    name = models.CharField(max_length=128)
    description = models.TextField(blank=True)


class DescriptionLibrary(BaseModel):
    name = models.CharField(max_length=128)
    linked_description = models.TextField(verbose_name='Description', blank=True)


class EstimateTemplate(BaseModel):
    name = models.CharField(max_length=128)
    assembles = models.ManyToManyField(Assemble, related_name='estimate_templates', blank=True)
    contact_description = models.TextField(blank=True, default='')


class DataView(BaseModel):
    name = models.CharField(verbose_name='Formula Name', max_length=128)
    formula = models.TextField(verbose_name='Formula')
    estimate_template = models.ForeignKey('sales.EstimateTemplate', on_delete=models.CASCADE, related_name='data_views',
                                          null=True, blank=True)
