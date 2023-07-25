from django.contrib.auth.models import Group, Permission
from rest_framework import serializers

from api.models import GroupCompany


class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ('id', 'name', 'permissions')

    def create(self, validated_data):
        company = self.context['request'].user.company
        instance = super().create(validated_data)
        GroupCompany.objects.create(company=company, group=instance)
        return instance


class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ('id', 'name', 'content_type')
        read_only_fields = ('content_type',)
