from datetime import datetime

from django.db.models import Value, Q, Prefetch, Subquery
from rest_framework import generics, permissions, status, filters as rf_filters
from django_filters import rest_framework as filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.generics import get_object_or_404
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response

from sales.filters.estimate import FormulaFilter, EstimateTemplateFilter, AssembleFilter, GroupFormulaFilter
from sales.models import DataPoint, Catalog
from sales.models.estimate import POFormula, POFormulaGrouping, DataEntry, UnitLibrary, \
    DescriptionLibrary, Assemble, EstimateTemplate
from sales.serializers.estimate import POFormulaSerializer, POFormulaGroupingSerializer, DataEntrySerializer, \
    UnitLibrarySerializer, DescriptionLibrarySerializer, LinkedDescriptionSerializer, AssembleSerializer, \
    EstimateTemplateSerializer, TaggingSerializer
from sales.views.catalog import parse_c_table


class POFormulaList(generics.ListCreateAPIView):
    queryset = POFormula.objects.all().prefetch_related('self_data_entries').select_related('assemble',
                                                                                            'group').order_by(
        '-modified_date')
    serializer_class = POFormulaSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = FormulaFilter


class POFormulaDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = POFormula.objects.all().prefetch_related('self_data_entries')
    serializer_class = POFormulaSerializer
    permission_classes = [permissions.IsAuthenticated]


class POFormulaGroupingList(generics.ListCreateAPIView):
    queryset = POFormulaGrouping.objects.all().order_by('-modified_date').distinct()
    serializer_class = POFormulaGroupingSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = GroupFormulaFilter

    def get_queryset(self):
        created_date = self.request.query_params.get('created_date')
        modified_date = self.request.query_params.get('modified_date')
        filter_params = self.request.query_params
        q = Q()
        for key, value in filter_params.items():
            if key in self.filterset_class.get_fields():
                if key != 'cost':
                    q &= Q(**{f'{key}__icontains': value})
                if key == 'cost' and value != str():
                    q &= Q(cost__gt=value)
        if created_date == str() or created_date is None:
            created_date = datetime.min

        if modified_date == str() or modified_date is None:
            modified_date = datetime.min

        formula_queryset = POFormula.objects.filter(q)
        grouping_queryset = POFormulaGrouping.objects.filter(
            created_date__gt=created_date,
            modified_date__gt=modified_date,
            group_formulas__in=Subquery(formula_queryset.values('pk'))
        ).order_by('-modified_date').distinct()

        for data in grouping_queryset:
            po = POFormula.objects.filter(Q(group=data), q)
            data.group_formulas.set(po)
        return grouping_queryset


class POFormulaGroupingDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = POFormulaGrouping.objects.all()
    serializer_class = POFormulaGroupingSerializer
    permission_classes = [permissions.IsAuthenticated]


class DataEntryList(generics.ListCreateAPIView):
    queryset = DataEntry.objects.all().order_by('-modified_date')
    serializer_class = DataEntrySerializer
    permission_classes = [permissions.IsAuthenticated]


class DataEntryDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = DataEntry.objects.all()
    serializer_class = DataEntrySerializer
    permission_classes = [permissions.IsAuthenticated]


class UnitLibraryList(generics.ListCreateAPIView):
    queryset = UnitLibrary.objects.all().order_by('-modified_date')
    serializer_class = UnitLibrarySerializer
    permission_classes = [permissions.IsAuthenticated]


class UnitLibraryDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = UnitLibrary.objects.all()
    serializer_class = UnitLibrarySerializer
    permission_classes = [permissions.IsAuthenticated]


class DescriptionLibraryList(generics.ListCreateAPIView):
    queryset = DescriptionLibrary.objects.all().order_by('-modified_date')
    serializer_class = DescriptionLibrarySerializer
    permission_classes = [permissions.IsAuthenticated]


class DescriptionLibraryDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = DescriptionLibrary.objects.all()
    serializer_class = DescriptionLibrarySerializer
    permission_classes = [permissions.IsAuthenticated]


class AssembleList(generics.ListCreateAPIView):
    queryset = Assemble.objects.filter(estimate_templates=None).order_by('-modified_date')
    serializer_class = AssembleSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = (filters.DjangoFilterBackend, rf_filters.SearchFilter)
    filterset_class = AssembleFilter
    search_fields = ('name', 'description')


class AssembleDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Assemble.objects.all()
    serializer_class = AssembleSerializer
    permission_classes = [permissions.IsAuthenticated]


class EstimateTemplateList(generics.ListCreateAPIView):
    queryset = EstimateTemplate.objects.all().order_by('-modified_date')
    serializer_class = EstimateTemplateSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = EstimateTemplateFilter


class EstimateTemplateDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = EstimateTemplate.objects.all()
    serializer_class = EstimateTemplateSerializer
    permission_classes = [permissions.IsAuthenticated]


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def filter_group_fo_to_fo(request):
    q = Q()
    temp = request.query_params.dict()
    for data in temp:
        if data != 'cost' and data != 'limit' and data != 'offset':
            q &= Q(**{f'{data}__icontains': temp[data]})
        if data == 'cost' and temp[data] != str():
            q &= Q(cost__gt=temp[data])
    formula_queryset = POFormula.objects.filter(q)
    grouping_queryset = POFormulaGrouping.objects.filter(
        group_formulas__in=Subquery(formula_queryset.values('pk'))
    ).order_by('-modified_date').distinct().values()

    for data in grouping_queryset:
        po = POFormula.objects.filter(Q(group_id=data['id']) & q).values()
        data['group_formulas'] = po
    paginator = LimitOffsetPagination()
    grouping_po_rs = paginator.paginate_queryset(grouping_queryset, request)
    serializer = POFormulaGroupingSerializer(grouping_po_rs, many=True)
    return Response(status=status.HTTP_200_OK, data=serializer.data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_linked_descriptions(request):
    """
    Get linked description from estimate and catalog
    """
    search_query = {'linked_description__icontains': request.GET.get('search', '')}
    dl = DescriptionLibrary.objects.filter(**search_query)
    dp = DataPoint.objects.filter(**search_query)
    paginator = LimitOffsetPagination()
    estimate_result = paginator.paginate_queryset(dl, request)
    catalog_result = paginator.paginate_queryset(dp, request)
    estimate_serializer = LinkedDescriptionSerializer(estimate_result, many=True)
    catalog_serializer = LinkedDescriptionSerializer(catalog_result, many=True)
    return paginator.get_paginated_response(estimate_serializer.data + catalog_serializer.data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_linked_description(request, pk):
    """
    Get linked description from estimate and catalog
    """
    if 'estimate' in pk:
        obj = get_object_or_404(DescriptionLibrary.objects.all(), pk=pk.split(':')[1])
    else:
        obj = get_object_or_404(DataPoint.objects.all(), pk=pk.split(':')[1])
    serializer = LinkedDescriptionSerializer(obj)
    return Response(status=status.HTTP_200_OK, data=serializer.data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_tag_formula(request):
    formulas = POFormula.objects.all()
    serializer = TaggingSerializer(formulas, many=True)
    return Response(data=serializer.data, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_tag_data_point(request):
    data_points = DataPoint.objects.all()
    serializer = TaggingSerializer(data_points, many=True)
    return Response(data=serializer.data, status=status.HTTP_200_OK)


@api_view(['PUT'])
@permission_classes([permissions.IsAuthenticated])
def unlink_group(request):
    ids = request.data
    formulas = POFormula.objects.filter(id__in=ids)
    formulas.update(group=None)
    serializer = POFormulaSerializer(formulas, many=True)
    return Response(data=serializer.data, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_material_by_data_entry(request, pk):
    de = DataEntry.objects.get(pk=pk)
    categories = de.material_selections.all()
    children = Catalog.objects.none()
    for category in categories:
        children |= Catalog.objects.filter(pk__in=category.get_all_descendant())
    children = children.difference(Catalog.objects.filter(c_table=Value('{}')))
    data = parse_c_table(children)
    return Response(status=status.HTTP_200_OK, data=data)
