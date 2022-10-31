from ..models.catalog import Material, CostTable
from ..serializers import catalog
from ..filters.catalog import CatalogFilter

from rest_framework import generics, permissions
from django_filters import rest_framework as filters


class MaterialList(generics.ListCreateAPIView):

    queryset = Material.objects.all()
    serializer_class = catalog.MaterialSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = CatalogFilter


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
