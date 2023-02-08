from django.db import models

from api.models import BaseModel


class DataEntry(BaseModel):
    name = models.CharField(max_length=128)


class POFormula(BaseModel):

    class FormulaType(models.IntegerChoices):
        MATERIAL = 1, 'Material'
        LABOR = 2, 'Labor'
        RENTAL = 3, 'Rental'

    name = models.CharField(max_length=128)
    formula = models.CharField(max_length=256)
    text_formula = models.TextField(max_length=256)
    type = models.IntegerField(choices=FormulaType.choices, null=True, blank=True, default=None)
    group = models.ForeignKey('sales.POFormulaGrouping', null=True, blank=True,
                              on_delete=models.CASCADE, related_name='po_formula_groupings')


class POFormulaToDataEntry(BaseModel):
    data_entry = models.ForeignKey(DataEntry, on_delete=models.CASCADE, blank=True, null=True)
    po_formula = models.ForeignKey(POFormula, on_delete=models.CASCADE, blank=True,
                                   null=True, related_name='self_data_entries')
    value = models.CharField(max_length=32, blank=True)


class POFormulaGrouping(BaseModel):
    name = models.CharField(max_length=128)
