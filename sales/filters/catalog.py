from django_filters import rest_framework as filters

from sales.filters.estimate import FilterIDMixin
from sales.models.catalog import Catalog, CatalogLevel


class CatalogFilter(filters.FilterSet, FilterIDMixin):
    is_ancestor = filters.BooleanFilter('is_ancestor')
    level = filters.ModelChoiceFilter(queryset=CatalogLevel.objects.all())
    id = filters.ModelMultipleChoiceFilter(queryset=Catalog.objects.all(), method='get_by_id')

    class Meta:
        model = Catalog
        fields = ('is_ancestor', 'id')
