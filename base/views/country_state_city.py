from ..models.country_state_city import Country, State, City, ZipCode
from ..serializers import country_state_city

from rest_framework import generics, permissions
from rest_framework import filters as rf_filters


class CountryList(generics.ListAPIView):
    queryset = Country.objects.all()
    serializer_class = country_state_city.CountrySerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None


class CountryStateList(generics.ListAPIView):
    serializer_class = country_state_city.StateSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        return State.objects.filter(country_id=self.kwargs['pk_country'])


class CountryStateCityList(generics.ListAPIView):
    serializer_class = country_state_city.CitySerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        return City.objects.filter(country_id=self.kwargs['pk_country'], state_id=self.kwargs['pk_state'])


class Zipcode(generics.ListAPIView):
    queryset = ZipCode.objects.all()
    serializer_class = country_state_city.ZipcodeSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = (rf_filters.SearchFilter,)
    search_fields = ('zipcode',)
