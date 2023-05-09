from django.db import models
from django.contrib.postgres.fields import ArrayField

from api.models import BaseModel
from sales.models import Catalog


class UnitLibrary(BaseModel):
    name = models.CharField(max_length=128)
    description = models.TextField(default='', blank=True)


class DataEntry(BaseModel):

    name = models.CharField(max_length=128)
    unit = models.ForeignKey('sales.UnitLibrary', on_delete=models.SET_NULL,
                             blank=True, null=True, related_name='data_entries')
    is_dropdown = models.BooleanField(default=False)
    dropdown = ArrayField(models.JSONField(blank=True, null=True), default=list, blank=True)
    is_material_selection = models.BooleanField(default=False, blank=True, null=True)
    material_selections = models.ManyToManyField('sales.Catalog', blank=True,
                                                 related_name='data_entries', symmetrical=False)


class POFormula(BaseModel):

    name = models.CharField(max_length=128)
    linked_description = models.TextField(blank=True, default='')
    show_color = models.BooleanField(default=False)
    formula = models.TextField()
    group = models.ForeignKey('sales.POFormulaGrouping', blank=True, related_name='group_formulas', null=True, on_delete=models.SET_NULL)
    assemble = models.ForeignKey('sales.Assemble', blank=True, related_name='assemble_formulas', null=True, on_delete=models.SET_NULL)
    created_from = models.ForeignKey('self', related_name='clones', null=True, blank=True, on_delete=models.SET_NULL)
    is_show = models.BooleanField(default=True, blank=True)  # Only show formula page
    quantity = models.CharField(max_length=64, blank=True)
    markup = models.CharField(max_length=64, blank=True)
    charge = models.CharField(max_length=64, blank=True)
    material = models.TextField(blank=True)
    unit = models.CharField(max_length=32, blank=True)
    cost = models.IntegerField(blank=True, default=0)
    formula_mentions = models.CharField(blank=True, max_length=256)  # for FE
    formula_data_mentions = models.CharField(blank=True, max_length=256)  # for FE
    gross_profit = models.CharField(max_length=32, blank=True)
    description_of_formula = models.TextField(blank=True)
    formula_scenario = models.TextField(blank=True)
    material_data_entry = models.JSONField(blank=True, default=dict, null=True)
    formula_for_data_view = models.IntegerField(blank=True, default=0, null=True)  # Used for dataview in other model

    def parse_material(self):
        primary_key = eval(self.material)
        pk_catalog, row_index = primary_key.get('id').split(':')
        return pk_catalog, row_index

    def get_link_catalog_by_material(self):
        try:
            pk_catalog, _ = self.parse_material()
            catalog = Catalog.objects.get(pk=pk_catalog)
            return catalog.get_full_ancestor()
        except:
            return []


class POFormulaToDataEntry(BaseModel):
    data_entry = models.ForeignKey(DataEntry, on_delete=models.CASCADE, blank=True, null=True)
    po_formula = models.ForeignKey(POFormula, on_delete=models.CASCADE, blank=True,
                                   null=True, related_name='self_data_entries')
    value = models.CharField(verbose_name='Default Value', max_length=32, blank=True)
    index = models.IntegerField(blank=True, default=0, null=True)
    dropdown_value = models.JSONField(blank=True, default=dict)
    material_value = models.JSONField(blank=True, default=dict)
    estimate_template = models.ForeignKey('sales.EstimateTemplate', on_delete=models.CASCADE,
                                          blank=True, null=True, related_name='data_entries')
    copies_from = ArrayField(models.JSONField(blank=True, default=dict, null=True), default=list, blank=True, null=True)
    name = models.CharField(blank=True, default='', max_length=128)


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
    proposal_name = models.CharField(max_length=128, blank=True, default='')
    assembles = models.ManyToManyField(Assemble, related_name='estimate_templates', blank=True)
    contact_description = models.TextField(blank=True, default='')
    catalog_links = ArrayField(models.CharField(max_length=128, blank=True, default=''), default=list, blank=True)
    group_by_proposal = models.ForeignKey('sales.GroupByEstimate', on_delete=models.CASCADE,
                                          related_name='estimate_templates', null=True, blank=True)
    price_comparison = models.ForeignKey('sales.PriceComparison', on_delete=models.CASCADE,
                                         related_name='estimate_templates', null=True, blank=True)
    is_show = models.BooleanField(default=True, blank=True)
    original = models.IntegerField(default=0, blank=True, null=True)


class DataView(BaseModel):
    name = models.CharField(verbose_name='Formula Name', max_length=128)
    formula = models.TextField(verbose_name='Formula', blank=True)
    estimate_template = models.ForeignKey('sales.EstimateTemplate', on_delete=models.CASCADE, related_name='data_views',
                                          null=True, blank=True)
    index = models.IntegerField(blank=True, default=0, null=True)
