from django_filters import rest_framework as filters

from sales.models.catalog import Catalog, CatalogLevel


class CatalogFilter(filters.FilterSet):
    is_ancestor = filters.BooleanFilter('is_ancestor')
    level = filters.ModelChoiceFilter(queryset=CatalogLevel.objects.all())

    class Meta:
        model = Catalog
        fields = ('is_ancestor',)
