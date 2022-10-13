from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework.response import Response

from ..models import catalog


class MaterialSerializer(serializers.ModelSerializer):
    class Meta:
        model = catalog.Material
        fields = ('id', 'type', 'name', 'parent', 'sequence', 'cost_table')
