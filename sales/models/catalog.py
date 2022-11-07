from django.db import models

from api.models import BaseModel


class CostTable(models.Model):
    class Meta:
        db_table = 'cost_table'

    name = models.CharField(max_length=128)
    data = models.JSONField(default=dict)

    def __str__(self):
        return self.name


class Catalog(BaseModel):

    class Meta:
        db_table = 'catalog'
        ordering = ['-modified_date']

    sequence = models.IntegerField(default=0)
    name = models.CharField(max_length=128)
    parents = models.ManyToManyField('self', related_name='children', blank=True)
    type = models.CharField(max_length=128, null=True, blank=True)
    cost_table = models.OneToOneField(CostTable, on_delete=models.CASCADE, null=True, blank=True)
    icon = models.ImageField(upload_to='catalog/%Y/%m/%d/', blank=True)

    def __str__(self):
        return self.name

    def link(self, pk):
        catalog = Catalog.objects.get(pk=pk)
        catalog.children.add(self)

    def duplicate(self, pk):
        pass
