from django.db import models

from api.models import BaseModel


class CatalogLevel(models.Model):
    class Meta:
        db_table = 'catalog_level'

    name = models.CharField(max_length=64)
    parent = models.ForeignKey('self', related_name='child', null=True,
                               blank=True, on_delete=models.CASCADE, default=None)

    def __str__(self):
        return self.name

    def get_all_descendant(self):
        ids = [self.pk]
        try:
            catalog_level = CatalogLevel.objects.get(parent__id=self.pk)
            ids.extend(catalog_level.get_all_descendant())
        except CatalogLevel.DoesNotExist:
            pass
        return ids


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
    is_ancestor = models.BooleanField(default=False, blank=True)
    parents = models.ManyToManyField('self', related_name='children', blank=True)
    cost_table = models.OneToOneField(CostTable, on_delete=models.CASCADE, null=True, blank=True)
    icon = models.ImageField(upload_to='catalog/%Y/%m/%d/', blank=True)
    level = models.ForeignKey(CatalogLevel, on_delete=models.CASCADE, null=True, blank=True, default=None)

    def __str__(self):
        return self.name

    def get_tree_view(self):
        pass

    def link(self, pk):
        catalog = Catalog.objects.get(pk=pk)
        catalog.children.add(self)

    def duplicate(self, pk):
        pass
