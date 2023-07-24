from django.contrib.auth.models import Group, Permission
from django_filters import rest_framework as filters
from rest_framework import generics, permissions
from rest_framework import filters as rf_filters

from base.models.config import PersonalInformation
from base.serializers.auth import GroupSerializer, PermissionSerializer
from base.serializers.config import PersonalInformationSerializer


class GroupList(generics.ListCreateAPIView):
    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    permission_classes = [permissions.IsAuthenticated]


class GroupDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    permission_classes = [permissions.IsAuthenticated]


class PermissionList(generics.ListCreateAPIView):
    queryset = Permission.objects.all()
    serializer_class = PermissionSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None


class PermissionDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Permission.objects.all()
    serializer_class = PermissionSerializer
    permission_classes = [permissions.IsAuthenticated]


class PersonalInformationView(generics.ListCreateAPIView):
    queryset = PersonalInformation.objects.all()
    serializer_class = PersonalInformationSerializer
    permission_classes = [permissions.IsAuthenticated]


class PersonalInformationDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = PersonalInformation.objects.all()
    serializer_class = PersonalInformationSerializer
    permission_classes = [permissions.IsAuthenticated]
