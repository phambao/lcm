from rest_framework import serializers
from ..models.column import Column


class ColumnSerializer(serializers.ModelSerializer):
    class Meta:
        model = Column
        fields = ('id', 'name', 'params', 'content_type', 'user')
