from django.contrib.auth import get_user_model
from rest_framework import serializers

from ..models.lead_list import LeadDetail


class LeadDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeadDetail
        fields = '__all__'
