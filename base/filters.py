from django_filters import rest_framework as filters
from base.models.config import Search, Column, Config
from django.contrib.contenttypes.models import ContentType


class CountryStateCityBaseFilter:
    """
    Filter Country, State and City
    """

    def filter_city_id(self, queryset, name, value):
        return queryset.filter(city__id=value)

    def filter_state_id(self, queryset, name, value):
        return queryset.filter(state__id=value)

    def filter_country_id(self, queryset, name, value):
        return queryset.filter(country__id=value)


class SearchFilter(filters.FilterSet):
    content_type = filters.ModelChoiceFilter(queryset=ContentType.objects.all())

    class Meta:
        model = Search
        fields = ('content_type', )


class ColumnFilter(filters.FilterSet):
    content_type = filters.ModelChoiceFilter(queryset=ContentType.objects.all())

    class Meta:
        model = Column
        fields = ('content_type', )


class ConfigFilter(filters.FilterSet):
    content_type = filters.ModelChoiceFilter(queryset=ContentType.objects.all())

    class Meta:
        model = Config
        fields = ('content_type',)
