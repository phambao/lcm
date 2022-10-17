from rest_framework import serializers
from api.serializers.base import SerializerMixin
from ..models import country_state_city


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
