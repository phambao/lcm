from django.contrib.auth import get_user_model
from rest_framework import serializers

from ..models.lead_list import LeadDetail, LeadPartner, Activities


class ActivitiesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Activities
        fields = '__all__'


class LeadDetailSerializer(serializers.ModelSerializer):

    class Meta:
        model = LeadDetail
        fields = '__all__'


class LeadDetailCreateSerializer(serializers.ModelSerializer):
    activities = ActivitiesSerializer('lead', many=True, allow_null=True)

    class Meta:
        model = LeadDetail
        fields = '__all__'
