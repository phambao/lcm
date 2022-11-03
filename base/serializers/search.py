from rest_framework import serializers
from ..models.search import Search


class SearchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Search
        fields = ('id', 'name', 'params', 'content_type', 'user')
