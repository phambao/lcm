from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from ..models.catalog import Catalog, CostTable
from ..serializers import catalog
from ..filters.catalog import CatalogFilter

from rest_framework import generics, permissions, status
from django_filters import rest_framework as filters


class CatalogList(generics.ListCreateAPIView):

    queryset = Catalog.objects.all()
    serializer_class = catalog.CatalogSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = CatalogFilter


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


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_catalog_children(request, pk):
    catalogs = Catalog.objects.filter(parents__id=pk)
    serializer = catalog.CatalogSerializer(catalogs, many=True)
    return Response(status=status.HTTP_200_OK, data=serializer.data)
