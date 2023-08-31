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
    address = kwargs.get('address')
    key = config('GOOGLE_MAPS_API_KEY')
    url = f'https://maps.googleapis.com/maps/api/geocode/json?address={address}&key={key}'
    try:
        response = requests.get(url)
        if response.status_code == status.HTTP_200_OK:
            return Response(status=status.HTTP_200_OK, data=response.json())

        elif response.status_code == status.HTTP_400_BAD_REQUEST:
            return Response(status=status.HTTP_400_BAD_REQUEST, data={'error': response.reason})

        elif response.status_code == status.HTTP_403_FORBIDDEN:
            return Response(status=status.HTTP_403_FORBIDDEN, data={'error': response.reason})

        elif response.status_code == status.HTTP_409_CONFLICT:
            return Response(status=status.HTTP_409_CONFLICT, data={'error': response.reason})

        elif response.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
            return Response(status=status.HTTP_429_TOO_MANY_REQUESTS, data={'error': response.reason})

        elif response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR:
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR, data={'error': response.reason})

        elif response.status_code == status.HTTP_501_NOT_IMPLEMENTED:
            return Response(status=status.HTTP_501_NOT_IMPLEMENTED, data={'error': response.reason})

        elif response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE:
            return Response(status=status.HTTP_503_SERVICE_UNAVAILABLE, data={'error': response.reason})

        elif response.status_code == status.HTTP_504_GATEWAY_TIMEOUT:
            return Response(status=status.HTTP_504_GATEWAY_TIMEOUT, data={'error': response.reason})

        elif response.status_code == status.HTTP_401_UNAUTHORIZED:
            return Response(status=status.HTTP_401_UNAUTHORIZED, data={'error': response.reason})

        elif response.status_code == status.HTTP_404_NOT_FOUND:
            return Response(status=status.HTTP_404_NOT_FOUND, data={'error': response.reason})

    except Exception as e:
        return Response(status=status.HTTP_404_NOT_FOUND, data={'error': 'An error occurred'})

