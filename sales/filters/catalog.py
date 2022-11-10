from django_filters import rest_framework as filters
from sales.models.catalog import Catalog


class CatalogFilter(filters.FilterSet):
    is_ancestor = filters.BooleanFilter('is_ancestor')

    class Meta:
        model = Catalog
        fields = ('is_ancestor', )
