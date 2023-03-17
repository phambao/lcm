from django.db import models

from api.models import BaseModel


class UnitLibrary(BaseModel):
    name = models.CharField(max_length=128)
    description = models.TextField(default='', blank=True)


class TemplateName(BaseModel):

    class EstimateTemplateName(models.IntegerChoices):
        ESTIMATE_TEMPLATE = 1, 'Estimate Template'
        FORMULA_CENTER = 2, 'Formula Center'
        ASSEMBLE = 3, 'Assemble'
        DESCRIPTION = 4, 'Description'
        DATA_ENTRY = 5, 'Data Entry'
        UNIT = 6, 'Unit'

    name = models.CharField(max_length=128)
    parent = models.ForeignKey('sales.TemplateName', on_delete=models.SET_NULL,
                               blank=True, related_name='children', null=True)
    menu = models.IntegerField(choices=EstimateTemplateName.choices, blank=True, null=True)


class DataEntry(BaseModel):
    name = models.CharField(max_length=128)
    value = models.CharField(max_length=32, blank=True)
    unit = models.ForeignKey('sales.UnitLibrary', on_delete=models.SET_NULL,
                             blank=True, null=True, related_name='data_entries')


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
    material = models.CharField(max_length=8, blank=True)
    unit = models.CharField(max_length=32, blank=True)
    cost = models.IntegerField(blank=True, default=0)


class POFormulaToDataEntry(BaseModel):
    data_entry = models.ForeignKey(DataEntry, on_delete=models.CASCADE, blank=True, null=True)
    po_formula = models.ForeignKey(POFormula, on_delete=models.CASCADE, blank=True,
                                   null=True, related_name='self_data_entries')
    value = models.CharField(verbose_name='Default Value', max_length=32, blank=True)


class POFormulaGrouping(BaseModel):
    name = models.CharField(max_length=128)


class Assemble(BaseModel):
    name = models.CharField(max_length=128)


class DescriptionLibrary(BaseModel):
    name = models.CharField(max_length=128)
    linked_description = models.TextField(verbose_name='Description', blank=True)
