from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from ..models.catalog import Catalog, CostTable, CatalogLevel
from ..serializers import catalog
from ..filters.catalog import CatalogFilter

from rest_framework import generics, permissions, status, filters as rf_filters
from django_filters import rest_framework as filters


class CatalogList(generics.ListCreateAPIView):

    queryset = Catalog.objects.all()
    serializer_class = catalog.CatalogSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = (filters.DjangoFilterBackend, rf_filters.SearchFilter)
    filterset_class = CatalogFilter
    search_fields = ('name',)


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


class CatalogLevelList(generics.ListCreateAPIView):
    queryset = CatalogLevel.objects.all()
    serializer_class = catalog.CatalogLevelModelSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        catalog = get_object_or_404(Catalog.objects.all(), pk=self.kwargs['pk_catalog'])
        return catalog.all_levels.all()

    def perform_create(self, serializer):
        instance = serializer.save()
        instance.catalog_id = self.kwargs['pk_catalog']
        instance.save()


class CatalogLevelDetail(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = catalog.CatalogLevelModelSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        catalog = get_object_or_404(Catalog.objects.all(), pk=self.kwargs['pk_catalog'])
        return catalog.all_levels.all()


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_catalog_children(request, pk):
    level = None
    catalogs = Catalog.objects.filter(parents__id=pk)
    for c in catalogs:
        if c.level:
            level = c.level
            break
    if level:
        catalogs = Catalog.objects.filter(parents__id=pk, level=level)

    serializer = catalog.CatalogSerializer(catalogs, many=True)
    return Response(status=status.HTTP_200_OK, data=serializer.data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_catalog_levels(request, pk):
    level = None
    catalogs = Catalog.objects.filter(parents__id=pk)
    for c in catalogs:
        if c.level:
            level = c.level
            break

    if not level:
        return Response(status=status.HTTP_200_OK, data=[])

    catalog_level = CatalogLevel.objects.get(pk=level.pk)
    catalog_level_ids = catalog_level.get_all_descendant()
    all_catalog_level_descendant = CatalogLevel.objects.filter(pk__in=catalog_level_ids)
    serializer = catalog.CatalogLevelModelSerializer(all_catalog_level_descendant, many=True)
    return Response(status=status.HTTP_200_OK, data=serializer.data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_catalog_tree(request, pk):
    catalog = Catalog.objects.get(pk=pk)
    catalog_tree = catalog.get_tree_view()
    return Response(status=status.HTTP_200_OK, data=catalog_tree)


@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
def delete_catalogs(request):
    ids = request.data
    catalogs = Catalog.objects.filter(pk__in=ids)
    for catalog in catalogs:
        catalog.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)
