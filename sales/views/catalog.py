from ..models.catalog import Catalog, CostTable
from ..serializers import catalog

from rest_framework import generics, permissions


class CatalogList(generics.ListCreateAPIView):

    queryset = Catalog.objects.all()
    serializer_class = catalog.CatalogSerializer
    permission_classes = [permissions.IsAuthenticated]


class CatalogDetail(generics.RetrieveUpdateDestroyAPIView):

    queryset = Catalog.objects.all()
    serializer_class = catalog.CatalogSerializer
    permission_classes = [permissions.IsAuthenticated]


class CostTableList(generics.ListCreateAPIView):

    queryset = CostTable.objects.all()
    serializer_class = catalog.CostTableModelSerializer
    permission_classes = [permissions.IsAuthenticated]


class CostTableDetail(generics.RetrieveUpdateDestroyAPIView):

    queryset = CostTable.objects.all()
    serializer_class = catalog.CostTableModelSerializer
    permission_classes = [permissions.IsAuthenticated]
