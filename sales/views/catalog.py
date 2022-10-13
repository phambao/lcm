from ..models.catalog import Material
from ..serializers import catalog

from rest_framework import generics, permissions


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
