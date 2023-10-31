import copy
from functools import lru_cache

from django.db import models

from api.models import BaseModel


class DataPointUnit(BaseModel):
    name = models.CharField(max_length=128)


class CatalogLevel(BaseModel):
    class Meta:
        db_table = 'catalog_level'

    name = models.CharField(max_length=64)
    parent = models.OneToOneField('self', related_name='child', null=True,
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
            child_level.parent = copy.copy(self.parent)

        super(CatalogLevel, self).delete(using=using, keep_parents=keep_parents)
        if has_child:
            child_level.save()

    def get_ordered_descendant(self):
        descendant = [self]
        try:
            catalog_level = CatalogLevel.objects.get(parent__id=self.pk)
            descendant.extend(catalog_level.get_ordered_descendant())
        except CatalogLevel.DoesNotExist:
            pass
        return descendant


class DataPoint(BaseModel):
    class Meta:
        db_table = 'data_point'

    class Unit(models.TextChoices):
        INCHES = 'in', 'inches'
        METERS = 'm', 'meters'
        EMPTY = '', ''

    value = models.CharField(max_length=128, blank=True)
    unit = models.ForeignKey('sales.UnitLibrary', on_delete=models.CASCADE, null=True, blank=True)
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
    c_table = models.JSONField(default=dict, blank=True)
    icon = models.TextField(blank=True)
    level = models.ForeignKey(CatalogLevel, on_delete=models.CASCADE, null=True,
                              blank=True, default=None, related_name='catalogs')
    level_index = models.IntegerField(default=0, blank=True, null=True)

    def __str__(self):
        return self.name

    def get_all_descendant(self, have_self=False):
        """Get all descendant of this catalog. Return a list of id"""
        descendants = []
        if have_self:
            descendants = [self.pk]
        catalogs = Catalog.objects.filter(parents__id=self.pk)
        for c in catalogs:
            descendants.append(c.pk)
            descendants.extend(c.get_all_descendant(have_self=have_self))
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
            'icon': self.icon,
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

    @lru_cache(128)
    def get_full_ancestor(self):
        ancestor = self.get_ancestors()
        first_ancestor = ancestor[-1]
        ancestor.append(first_ancestor.parents.first())
        first_ancestor = ancestor[-1]
        ancestor.append(first_ancestor.parents.first())
        return ancestor

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

    def get_unique_name(self, parent):
        """
        Assume that category like a folder, we prevent the same name in that folder
        """
        try:
            names = Catalog.objects.filter(parents=parent, level=self.level).values_list('name', flat=True)
        except AttributeError:
            return ''
        name = self.name
        if name not in names:
            return name
        i = 1
        while name in names:
            if name.split(' ')[-1].isdigit():
                name = ' '.join(name.split(' ')[:-1]) + ' ' + str(i)
            else:
                name = name + f' {i}'
            i += 1
        return name

    def clone(self, parent=None, data_points=[]):
        c = copy.copy(self)
        c.id = None
        c.sequence = self.sequence + 1
        c.name = c.get_unique_name(parent) or self.get_unique_name(parent)
        c.save()
        if parent:
            c.parents.add(parent)
        points = self.data_points.filter(id__in=data_points)
        d_points = []
        for p in points:
            params = {'value': p.value,
                      'unit_id': p.unit_id,
                      'linked_description': p.linked_description,
                      'is_linked': p.is_linked,
                      'catalog_id': c.id}
            d_points.append(DataPoint(**params))
        DataPoint.objects.bulk_create(d_points)
        return c

    def duplicate(self, parent=None, depth=0, data_points=[]):
        """
        duplicate by depth (level)
        """
        c = self.clone(parent=parent, data_points=data_points)
        if depth:
            children = Catalog.objects.filter(parents__id=self.pk)
            for child in children:
                child.duplicate(parent=c, depth=depth-1, data_points=data_points)
        return c

    def duplicate_by_catalog(self, parent=None, descendant=[], data_points=[]):
        """
        duplicate by descendant
        """
        c = self.clone(parent=parent, data_points=data_points)
        if descendant:
            children = Catalog.objects.filter(parents__id=self.pk, id__in=descendant)
            for child in children:
                child.duplicate_by_catalog(parent=c, descendant=descendant, data_points=data_points)

    def get_ancestor_linked_description(self):
        catalogs = self.get_ancestors()
        data_points = DataPoint.objects.filter(catalog__in=catalogs)
        return data_points

    def get_material(self, material):
        """
        Parameters:
            material: "catalog_id:row_index"
        """
        pk_catalog, row_index = material.split(':')
        pk_catalog, row_index = int(pk_catalog), int(row_index)
        try:
            d = self.c_table['data'][row_index]
            header = self.c_table['header']
            return {**{header[i]: d[i] for i in range(len(header))}, **{"id": f'{self.pk}:{row_index}'}}
        except (KeyError, IndexError):
            return {}
