from django.db import models

from api.models import BaseModel


class UnitLibrary(BaseModel):
    name = models.CharField(max_length=128)


class TemplateName(BaseModel):

    class EstimateTemplateName(models.IntegerChoices):
        ESTIMATE_TEMPLATE = 1, 'Estimate Template'
        FORMULA_CENTER = 2, 'Formula Center'
        LIBRARY = 3, 'Library'

    name = models.CharField(max_length=128)
    parent = models.ForeignKey('sales.TemplateName', on_delete=models.SET_NULL,
                               blank=True, related_name='children', null=True)
    menu = models.IntegerField(choices=EstimateTemplateName.choices, blank=True, null=True)


class DataEntry(BaseModel):
    name = models.CharField(max_length=128)


class POFormula(BaseModel):

    name = models.CharField(max_length=128)
    formula = models.CharField(max_length=256)
    text_formula = models.TextField(max_length=256)
    type = models.ForeignKey('sales.Catalog', null=True, blank=True,
                             on_delete=models.SET_NULL, related_name='formulas')
    group = models.ForeignKey('sales.POFormulaGrouping', null=True, blank=True,
                              on_delete=models.CASCADE, related_name='po_formula_groupings')
    related_formulas = models.ManyToManyField('self', related_name='used_by', symmetrical=False, blank=True)


class POFormulaToDataEntry(BaseModel):
    data_entry = models.ForeignKey(DataEntry, on_delete=models.CASCADE, blank=True, null=True)
    po_formula = models.ForeignKey(POFormula, on_delete=models.CASCADE, blank=True,
                                   null=True, related_name='self_data_entries')
    value = models.CharField(max_length=32, blank=True)


class POFormulaGrouping(BaseModel):
    name = models.CharField(max_length=128)
