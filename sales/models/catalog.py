import copy

from django.db import models

from api.models import BaseModel


class DataPointUnit(BaseModel):
    name = models.CharField(max_length=128, unique=True)


class CatalogLevel(models.Model):
    class Meta:
        db_table = 'catalog_level'

    name = models.CharField(max_length=64)
    parent = models.ForeignKey('self', related_name='child', null=True,
                               blank=True, on_delete=models.SET_NULL, default=None)
    catalog = models.ForeignKey('Catalog', on_delete=models.CASCADE, null=True,
                                blank=True, default=None, related_name='all_levels')

    def __str__(self):
        return self.name

    def delete(self, using=None, keep_parents=False):
        child_level = CatalogLevel.objects.filter(parent=self)
        has_child = child_level.exists()

        if has_child:
            catalogs = Catalog.objects.filter(level=self)
            for c in catalogs:
                children = Catalog.objects.filter(parents=c)
                parent = c.parents.first()
                for child in children:
                    child.parents.clear()
                    child.parents.add(parent)
            child_level = child_level.first()
            child_level.parent = self.parent
            child_level.save()

        super(CatalogLevel, self).delete(using=using, keep_parents=keep_parents)

    def get_ordered_descendant(self):
        descendant = [self]
        try:
            catalog_level = CatalogLevel.objects.get(parent__id=self.pk)
            descendant.extend(catalog_level.get_ordered_descendant())
        except CatalogLevel.DoesNotExist:
            pass
        return descendant


class CostTable(models.Model):
    class Meta:
        db_table = 'cost_table'

    name = models.CharField(max_length=128)
    data = models.JSONField(default=dict)

    def __str__(self):
        return self.name


class DataPoint(models.Model):
    class Meta:
        db_table = 'data_point'
        
    class Unit(models.TextChoices):
        INCHES = 'in', 'inches'
        METERS = 'm', 'meters'
        EMPTY = '', ''

    value = models.CharField(max_length=128, blank=True)
    unit = models.ForeignKey(DataPointUnit, on_delete=models.CASCADE, null=True, blank=True)
    linked_description = models.CharField(max_length=128, blank=True)
    is_linked = models.BooleanField(default=False)
    catalog = models.ForeignKey('Catalog', on_delete=models.CASCADE, related_name='data_points',
                                null=True, blank=True)


class Catalog(BaseModel):

    class Meta:
        db_table = 'catalog'
        ordering = ['-modified_date']

    sequence = models.IntegerField(default=0)
    name = models.CharField(max_length=128)
    is_ancestor = models.BooleanField(default=False, blank=True)
    parents = models.ManyToManyField('self', related_name='children', blank=True, symmetrical=False)
    cost_table = models.OneToOneField(CostTable, on_delete=models.CASCADE, null=True, blank=True)
    c_table = models.JSONField(default=dict, blank=True)
    icon = models.ImageField(upload_to='catalog/%Y/%m/%d/', blank=True)
    level = models.ForeignKey(CatalogLevel, on_delete=models.CASCADE, null=True,
                              blank=True, default=None, related_name='catalogs')
    level_index = models.IntegerField(default=0, blank=True, null=True)

    def __str__(self):
        return self.name

    def get_all_descendant(self):
        """Get all descendant of this catalog. Return a list of id"""
        descendants = []
        catalogs = Catalog.objects.filter(parents__id=self.pk)
        for c in catalogs:
            descendants.append(c.pk)
            descendants.extend(c.get_all_descendant())
        return descendants
    
    def get_tree_view(self):
        tree = []
        catalogs = Catalog.objects.filter(parents__id=self.pk)
        for c in catalogs:
            tree.append(c.get_tree_view())
        return {
            'id': self.pk,
            'name': self.name,
            'is_ancestor': self.is_ancestor,
            'parents': self.parents.all().values_list('pk', flat=True),
            'cost_table': self.cost_table,
            'icon': self.icon.url if self.icon else None,
            'level': self.level.id if self.level else None,
            'children': tree
        }

    def delete(self, *args, **kwargs):
        """Delete all descendant of this catalog (include itself)"""
        ids = self.get_all_descendant()
        catalogs = Catalog.objects.filter(pk__in=ids)
        catalogs.delete()
        return super(Catalog, self).delete(*args, **kwargs)

    def get_ancestors(self):
        ancester = [self]
        try:
            parent = self.parents.all()[0]
        except IndexError:
            return []
        if self.level:
            ancester.extend(parent.get_ancestors())
        else:
            return []
        return ancester

    def get_ordered_levels(self):
        """
        Ancestor level will be the first and descendant will be the last
        """
        levels = self.all_levels.all()
        ancester = levels.get(parent=None)
        return ancester.get_ordered_descendant()

    def link(self, pk):
        catalog = Catalog.objects.get(pk=pk)
        catalog.children.add(self)

    def clone(self, parent=None):
        c = copy.copy(self)
        c.id = None
        c.sequence = self.sequence + 1
        c.save()
        if parent:
            c.parents.add(parent)
        return c

    def duplicate(self, parent=None, depth=0):
        c = self.clone(parent=parent)
        if depth:
            children = Catalog.objects.filter(parents__id=self.pk)
            for child in children:
                child.duplicate(parent=c, depth=depth-1)
