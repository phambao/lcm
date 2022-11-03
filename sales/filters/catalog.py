from django_filters import rest_framework as filters
from sales.models.catalog import Catalog


class CatalogFilter(filters.FilterSet):
    parents = filters.BooleanFilter('parents', lookup_expr='isnull')

    class Meta:
        model = Catalog
        fields = ('parents', )
