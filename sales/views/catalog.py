from ..models.catalog import Material, CostTable
from ..serializers import catalog

from rest_framework import generics, permissions


class MaterialList(generics.ListCreateAPIView):

    queryset = Material.objects.all()
    serializer_class = catalog.MaterialSerializer
    permission_classes = [permissions.IsAuthenticated]


class MaterialDetail(generics.RetrieveUpdateDestroyAPIView):

    queryset = Material.objects.all()
    serializer_class = catalog.MaterialSerializer
    permission_classes = [permissions.IsAuthenticated]


class CostTableList(generics.ListCreateAPIView):

    queryset = CostTable.objects.all()
    serializer_class = catalog.CostTableModelSerializer
    permission_classes = [permissions.IsAuthenticated]


class CostTableDetail(generics.RetrieveUpdateDestroyAPIView):

    queryset = CostTable.objects.all()
    serializer_class = catalog.CostTableModelSerializer
    permission_classes = [permissions.IsAuthenticated]
