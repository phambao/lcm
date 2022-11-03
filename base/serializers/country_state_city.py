from rest_framework import serializers
from api.serializers.base import SerializerMixin
from . import base
from ..models import country_state_city


class ZipcodeSerializer(serializers.ModelSerializer, SerializerMixin):
    city = base.IDAndNameSerializer(allow_null=True, required=False)
    state = base.IDAndNameSerializer(allow_null=True, required=False)
    country = base.IDAndNameSerializer(allow_null=True, required=False)
    
    class Meta:
        model = country_state_city.ZipCode
        fields = ('id', 'zipcode', 'city', 'state', 'country')

class CitySerializer(serializers.ModelSerializer, SerializerMixin):
    class Meta:
        model = country_state_city.City
        fields = ('id', 'name')


class StateSerializer(serializers.ModelSerializer, SerializerMixin):
    class Meta:
        model = country_state_city.State
        fields = ('id', 'name')


class CountrySerializer(serializers.ModelSerializer, SerializerMixin):
    class Meta:
        model = country_state_city.Country
        fields = ('id', 'name')
