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
