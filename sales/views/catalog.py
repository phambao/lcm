from ..models.catalog import Material
from ..serializers import catalog

from rest_framework import generics, permissions
from rest_framework import viewsets, status
from rest_framework.response import Response
from django.shortcuts import get_object_or_404


class MaterialList(generics.ListCreateAPIView):
    """
    Used for get params
    """
    queryset = Material.objects.all()
    serializer_class = catalog.MaterialSerializer
    permission_classes = [permissions.IsAuthenticated]
    

class MaterialDetail(generics.RetrieveUpdateDestroyAPIView):
    """
    Used for get params
    """
    queryset = Material.objects.all()
    serializer_class = catalog.MaterialSerializer
    permission_classes = [permissions.IsAuthenticated]
