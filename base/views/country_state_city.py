import requests

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from ..constants import POSTAL_CODE, ADMINISTRATIVE_AREA_LEVEL_2, ADMINISTRATIVE_AREA_LEVEL_1, COUNTRY
from decouple import config


@api_view(['GET'])
def address_search(request, *args, **kwargs):
    data = request.query_params
    try:
        address = data['address']
        region = data.get('region')
        key = config('GOOGLE_MAPS_API_KEY')
        url = f'https://maps.googleapis.com/maps/api/place/autocomplete/json?input={address}&key={key}&language=en'
        response = requests.get(url)
        if response.status_code == status.HTTP_200_OK:
            return Response(status=status.HTTP_200_OK, data=response.json())
        else:
            return Response(status=response.status_code, data={'error': response.reason})

    except Exception as e:
        return Response(status=status.HTTP_404_NOT_FOUND, data={'error': 'get data location error'})


@api_view(['GET'])
def detail_location(request, place_id):
    try:
        key = config('GOOGLE_MAPS_API_KEY')
        url = f'https://maps.googleapis.com/maps/api/geocode/json?place_id={place_id}&key={key}&language=en'
        response = requests.get(url)
        if response.status_code == status.HTTP_200_OK:
            data_rs = {}
            data = response.json()
            address_components = data['results'][0]['address_components']
            data_rs['address'] = data['results'][0]["formatted_address"]
            data_rs['country'] = ''
            data_rs['state'] = ''
            data_rs['code'] = ''
            data_rs['city'] = ''
            for address_component in address_components:
                if COUNTRY in address_component['types']:
                    data_rs['country'] = address_component['long_name']

                if ADMINISTRATIVE_AREA_LEVEL_1 in address_component['types']:
                    data_rs['state'] = address_component['long_name']

                if ADMINISTRATIVE_AREA_LEVEL_2 in address_component['types']:
                    data_rs['city'] = address_component['long_name']

                if POSTAL_CODE in address_component['types']:
                    data_rs['code'] = address_component['long_name']

            if data_rs['city'] == '':
                data_rs['city'] = data_rs['state']

            return Response(status=status.HTTP_200_OK, data=data_rs)
        else:
            return Response(status=response.status_code, data={'error': response.reason})

    except Exception as e:
        return Response(status=status.HTTP_404_NOT_FOUND, data={'error': 'get data location error'})
