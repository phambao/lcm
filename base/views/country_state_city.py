import requests

from rest_framework import generics, permissions, status
from rest_framework import filters as rf_filters
from django_filters import rest_framework as filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from ..filters import CountryFilter
from ..models.country_state_city import Country, State, City, ZipCode
from ..serializers import country_state_city
from decouple import config

class CountryList(generics.ListAPIView):
    queryset = Country.objects.all()
    serializer_class = country_state_city.CountrySerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None


class CountryV2List(generics.ListAPIView):
    queryset = Country.objects.all()
    serializer_class = country_state_city.CountrySerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = (filters.DjangoFilterBackend, rf_filters.SearchFilter)
    filterset_class = CountryFilter
    search_fields = ('name', )


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


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def address_search(request, *args, **kwargs):
    data = request.query_params
    try:
        address = data['address']
        region = data.get('region')
        key = config('GOOGLE_MAPS_API_KEY')
        url = f'https://maps.googleapis.com/maps/api/place/autocomplete/json?input={address}&key={key}'
        response = requests.get(url)
        if response.status_code == status.HTTP_200_OK:
            return Response(status=status.HTTP_200_OK, data=response.json())
        else:
            return Response(status=response.status_code, data={'error': response.reason})

    except Exception as e:
        return Response(status=status.HTTP_404_NOT_FOUND, data={'error': 'get data location error'})


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def detail_location(request, place_id):
    try:
        key = config('GOOGLE_MAPS_API_KEY')
        url = f'https://maps.googleapis.com/maps/api/geocode/json?place_id={place_id}&key={key}'
        response = requests.get(url)
        if response.status_code == status.HTTP_200_OK:
            data_rs = {}
            data = response.json()
            address_components = data['results'][0]['address_components']
            data_rs['address'] = data['results'][0]["formatted_address"]
            for address_component in address_components:
                if 'country' in address_component['types']:
                    data_rs['country'] = address_component['long_name']

                if 'administrative_area_level_1' in address_component['types']:
                    data_rs['state'] = address_component['long_name']

                if 'administrative_area_level_2' in address_component['types']:
                    data_rs['city'] = address_component['long_name']

                if 'postal_code' in address_component['types']:
                    data_rs['code'] = address_component['long_name']

            return Response(status=status.HTTP_200_OK, data=data_rs)
        else:
            return Response(status=response.status_code, data={'error': response.reason})

    except Exception as e:
        return Response(status=status.HTTP_404_NOT_FOUND, data={'error': 'get data location error'})
