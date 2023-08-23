import io

from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.db.models import Value
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django_filters import rest_framework as filters
from openpyxl.reader.excel import load_workbook
from openpyxl.workbook import Workbook
from rest_framework import generics, permissions, status, filters as rf_filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from base.permissions import CatalogPermissions
from ..filters.catalog import CatalogFilter
from ..models.catalog import Catalog, CatalogLevel, DataPointUnit, DataPoint
from ..serializers import catalog
from ..serializers.catalog import CatalogEstimateSerializer
from api.middleware import get_request
from base.views.base import CompanyFilterMixin


class CatalogList(CompanyFilterMixin, generics.ListCreateAPIView):
    queryset = Catalog.objects.all().prefetch_related('data_points', 'parents')
    serializer_class = catalog.CatalogSerializer
    permission_classes = [permissions.IsAuthenticated & CatalogPermissions]
    filter_backends = (filters.DjangoFilterBackend, rf_filters.SearchFilter)
    filterset_class = CatalogFilter
    search_fields = ('name',)


class CatalogDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Catalog.objects.all().prefetch_related('data_points', 'parents')
    serializer_class = catalog.CatalogSerializer
    permission_classes = [permissions.IsAuthenticated & CatalogPermissions]

    def delete(self, request, *args, **kwargs):
        pk_catalog = kwargs.get('pk')
        data_catalog = catalog.Catalog.objects.filter(id=pk_catalog).first()
        c_table = data_catalog.c_table
        parent_catalog = data_catalog.parents.first()
        if parent_catalog:
            children_catalog = catalog.Catalog.objects.filter(parents=parent_catalog.id).count()
            if children_catalog <= 1:
                parent_catalog.c_table = c_table
                parent_catalog.save()

        return super().delete(request, *args, **kwargs)


class CatalogLevelList(generics.ListCreateAPIView):
    queryset = CatalogLevel.objects.all()
    serializer_class = catalog.CatalogLevelModelSerializer
    permission_classes = [permissions.IsAuthenticated & CatalogPermissions]

    def get_queryset(self):
        catalog = get_object_or_404(Catalog.objects.all(), pk=self.kwargs['pk_catalog'])
        try:
            ancester_level = catalog.all_levels.get(parent=None)
        except ObjectDoesNotExist:
            return []
        return ancester_level.get_ordered_descendant()

    def perform_create(self, serializer):
        instance = serializer.save()
        instance.catalog_id = self.kwargs['pk_catalog']
        instance.save()


class CatalogLevelDetail(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = catalog.CatalogLevelModelSerializer
    permission_classes = [permissions.IsAuthenticated & CatalogPermissions]

    def get_queryset(self):
        try:
            catalog = get_object_or_404(Catalog.objects.all(), pk=self.kwargs['pk_catalog'])
        except KeyError:
            # When swagger call this view, that doesn't pass param pk_catalog
            return CatalogLevel.objects.all()
        return catalog.all_levels.all()


class DataPointUnitView(CompanyFilterMixin, generics.ListCreateAPIView):
    serializer_class = catalog.DataPointUnitSerializer
    permission_classes = [permissions.IsAuthenticated & CatalogPermissions]
    queryset = DataPointUnit.objects.all()


class DataPointUnitDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = catalog.DataPointUnitSerializer
    permission_classes = [permissions.IsAuthenticated & CatalogPermissions]
    queryset = DataPointUnit.objects.all()


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated & CatalogPermissions])
def get_catalog_children(request, pk):
    level = None
    catalogs = Catalog.objects.filter(parents__id=pk)
    for c in catalogs:
        if c.level:
            level = c.level
            break
    if level:
        catalogs = Catalog.objects.filter(parents__id=pk, level=level)

    serializer = catalog.CatalogSerializer(catalogs, many=True, context={'request': request})
    return Response(status=status.HTTP_200_OK, data=serializer.data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated & CatalogPermissions])
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
    catalog_levels = catalog_level.get_ordered_descendant()
    serializer = catalog.CatalogLevelModelSerializer(catalog_levels, many=True)
    return Response(status=status.HTTP_200_OK, data=serializer.data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated & CatalogPermissions])
def get_catalog_tree(request, pk):
    catalog = get_object_or_404(Catalog, pk=pk)
    catalog_tree = catalog.get_tree_view()
    return Response(status=status.HTTP_200_OK, data=catalog_tree)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated & CatalogPermissions])
def get_catalog_list(request, pk):
    catalog_obj = get_object_or_404(Catalog, pk=pk)
    catalog_ids = catalog_obj.get_all_descendant()
    catalogs = Catalog.objects.filter(pk__in=catalog_ids).prefetch_related('data_points', 'parents')
    serializer = catalog.CatalogSerializer(catalogs, many=True, context={'request': request})
    return Response(status=status.HTTP_200_OK, data=serializer.data)


@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated & CatalogPermissions])
def delete_catalogs(request):
    ids = request.data
    catalogs = Catalog.objects.filter(pk__in=ids)
    for catalog in catalogs:
        catalog.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated & CatalogPermissions])
def get_catalog_ancestors(request):
    ids = request.GET.getlist('id', [])
    data = {}
    if ids:
        catalogs = Catalog.objects.filter(id__in=ids, company=get_request().user.company)
        for c in catalogs:
            navigation = c.get_ancestors()
            navigation = navigation[1:]
            data[c.pk] = [n.id for n in navigation[::-1]]
    return Response(status=status.HTTP_200_OK, data=data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated & CatalogPermissions])
def get_datapoint_by_catalog(request, pk):
    c = Catalog.objects.get(id=pk)
    serializer = catalog.DataPointSerializer(c.get_ancestor_linked_description(),
                                             many=True, context={'request': request})
    return Response(status=status.HTTP_200_OK, data=serializer.data)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated & CatalogPermissions])
def add_multiple_level(request):
    if isinstance(request.data, dict):
        catalog_serializer = catalog.CatalogSerializer(data=request.data.get('catalog'), context={'request': request})
        catalog_serializer.is_valid(raise_exception=True)
        c = catalog_serializer.save()
        parent = None
        data = []
        for name in request.data.get('levels', []):
            catalog_level = CatalogLevel.objects.create(name=name, parent=parent, catalog=c)
            parent = catalog_level
            data.append(catalog_level)
        serializer = catalog.CatalogLevelModelSerializer(data, many=True, context={'request': request})
        return Response(status=status.HTTP_201_CREATED, data={"levels": serializer.data,
                                                              "catalog": catalog_serializer.data})
    return Response(status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated & CatalogPermissions])
def duplicate_catalogs(request, pk):
    """
    Payload: [{"id": int, "depth": int, data_points: [id,...], descendant: [id,...]},...]
    """

    parent_catalog = get_object_or_404(Catalog, pk=pk)
    # duplicate by level
    if isinstance(request.data, list):
        for d in request.data:
            depth = int(d.get('depth', 0))
            data_points = d.get('data_points', [])
            try:
                c = Catalog.objects.get(pk=d.get('id'))
                c.duplicate(parent=parent_catalog, depth=depth, data_points=data_points)
            except Catalog.DoesNotExist:
                pass
        return Response(status=status.HTTP_201_CREATED, data={})
    return Response(status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated & CatalogPermissions])
def duplicate_catalogs_on_tree(request, pk):
    """
    Payload: {data_points: [id,...], descendant: [id,...], level: int}
    """
    parent_catalog = get_object_or_404(Catalog, pk=pk)
    if isinstance(request.data, dict):
        data_points = request.data.get('data_points', [])
        descendant = request.data.get('descendant', [])
        level = request.data.get('level', None)
        parents = Catalog.objects.filter(pk__in=descendant, level_id=level)
        for root in parents:
            try:
                root.duplicate_by_catalog(parent=parent_catalog, descendant=descendant,
                                          data_points=data_points)
            except Catalog.DoesNotExist:
                pass
        data = Catalog.objects.filter(pk__in=parent_catalog.get_all_descendant())
        serializer = catalog.CatalogSerializer(data, many=True, context={'request': request})
        return Response(status=status.HTTP_201_CREATED, data=serializer.data)
    return Response(status=status.HTTP_400_BAD_REQUEST)


@api_view(['PUT'])
@permission_classes([permissions.IsAuthenticated & CatalogPermissions])
@transaction.atomic
def swap_level(request, pk_catalog):
    """
    Payload: {"levels": [{"id": int, "parent": int},...], "catalogs": {"parent_id": [children_id,...],...}}
    """
    if isinstance(request.data, dict):
        ancestor_catalog = get_object_or_404(Catalog, pk=pk_catalog)
        try:
            levels = request.data.get('levels')
            catalogs = request.data.get('catalogs')

            updated_level = []
            level_id = []
            for l in levels:
                pk = l.get('id')
                level_id.append(pk)
                level = CatalogLevel.objects.get(pk=pk)
                level.parent_id = l.get('parent')
                updated_level.append(level)
            ancestor_catalog.all_levels.filter(pk__in=level_id).update(parent=None)
            CatalogLevel.objects.bulk_update(updated_level, fields=['parent'])

            # Validate level
            ordered_level = ancestor_catalog.get_ordered_levels()

            updated_catalog = []
            for key in catalogs.keys():
                parent_catalog = Catalog.objects.get(pk=key)
                children_catalog = Catalog.objects.filter(id__in=catalogs[key])
                for c in children_catalog:
                    c.parents.clear()
                    c.parents.add(parent_catalog)
                    c.level_index = ordered_level.index(c.level)
                    updated_catalog.append(c)

            # Validate catalog
            if Catalog.objects.filter(level__in=level_id).count() != len(updated_catalog):
                raise Exception('Missing or too much categories updated')

            # Update level index for all categories
            for l in ordered_level:
                Catalog.objects.filter(level=l).update(level_index=ordered_level.index(l))

            catalog_serializer = catalog.CatalogSerializer(updated_catalog, many=True,
                                                           context={'request': request})
            level_serializer = catalog.CatalogLevelModelSerializer(updated_level, many=True,
                                                                   context={'request': request})

            return Response(status=status.HTTP_200_OK, data={
                "levels": level_serializer.data,
                "catalog": catalog_serializer.data
            })
        except Exception as e:
            transaction.set_rollback(True)
            raise e
    return Response(status=status.HTTP_400_BAD_REQUEST)


def parse_c_table(children):
    data = []
    for child in children:
        try:
            try:
                ancestor = child.get_full_ancestor
                levels = [CatalogEstimateSerializer(c).data for c in ancestor[::-1]]
            except:
                levels = []
            c_table = child.c_table
            header = c_table['header']

            if len(header) >= 3:
                header[:3] = 'name', 'unit', 'cost'
            for i, d in enumerate(c_table['data']):
                content = {**{header[j]: d[j] for j in range(len(header))}, **{"id": f'{child.pk}:{i}'},
                           'levels': levels}
                data.append(content)
        except:
            """Some old data is not valid"""
    return data


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated & CatalogPermissions])
def get_materials(request):
    """
    Get cost table from ancestor catalog
    """
    filter_query = request.GET.get('catalog', None)
    if filter_query:
        c = get_object_or_404(Catalog.objects.all(), pk=filter_query)
        children = Catalog.objects.filter(
            pk__in=c.get_all_descendant(have_self=True)
        )
    else:
        children = Catalog.objects.filter(company=get_request().user.company)
    children = children.difference(Catalog.objects.filter(c_table=Value('{}')))
    data = parse_c_table(children)
    return Response(status=status.HTTP_200_OK, data=data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated & CatalogPermissions])
def export_catalog(request):
    workbook = Workbook()

    catalog_sheet = workbook.create_sheet(title='Catalog')
    level_sheet = workbook.create_sheet(title='Level')
    data_points_sheet = workbook.create_sheet(title='Data Point')

    catalog_fields = ['id', 'sequence', 'name', 'is_ancestor', 'c_table', 'icon', 'level', 'level_index', 'parents']
    catalog_sheet.append(catalog_fields)
    catalogs = Catalog.objects.filter(company=request.user.company).values_list(*catalog_fields)
    for c in catalogs:
        c = list(c)
        c[catalog_fields.index('c_table')] = str(c[catalog_fields.index('c_table')])
        catalog_sheet.append(c)

    level_fields = ['id', 'name', 'parent']
    level_sheet.append(level_fields)
    levels = CatalogLevel.objects.filter(company=request.user.company).values_list(*level_fields)
    for l in levels:
        level_sheet.append(l)

    point_fields = ['id', 'value', 'unit', 'linked_description', 'catalog', 'unit__name']
    data_points_sheet.append(point_fields)
    data_points = DataPoint.objects.filter(company=request.user.company).values_list(*point_fields)
    for data in data_points:
        data_points_sheet.append(data)

    workbook.remove(workbook['Sheet'])
    current_datetime = timezone.now().strftime("%Y%m%d_%H%M%S")
    filename = f"Catalog_{current_datetime}.xlsx"
    output = io.BytesIO()
    workbook.save(output)
    output.seek(0)
    response = FileResponse(output, as_attachment=True, filename=filename)
    return response


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated & CatalogPermissions])
def import_catalog(request):
    file = request.FILES['file']

    workbook = load_workbook(file)
    pass
