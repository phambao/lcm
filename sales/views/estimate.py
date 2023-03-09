from rest_framework import generics, permissions, status
from django_filters import rest_framework as filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.generics import get_object_or_404
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response

from sales.filters.estimate import TemplateNameFilter
from sales.models import DataPoint
from sales.models.estimate import POFormula, POFormulaGrouping, DataEntry, TemplateName, UnitLibrary, DescriptionLibrary
from sales.serializers.estimate import POFormulaSerializer, POFormulaGroupingSerializer, DataEntrySerializer, \
    TemplateNameSerializer, UnitLibrarySerializer, DescriptionLibrarySerializer, LinkedDescriptionSerializer


class POFormulaList(generics.ListCreateAPIView):
    queryset = POFormula.objects.all()
    serializer_class = POFormulaSerializer
    permission_classes = [permissions.IsAuthenticated]


class POFormulaDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = POFormula.objects.all()
    serializer_class = POFormulaSerializer
    permission_classes = [permissions.IsAuthenticated]


class POFormulaGroupingList(generics.ListCreateAPIView):
    queryset = POFormulaGrouping.objects.all()
    serializer_class = POFormulaGroupingSerializer
    permission_classes = [permissions.IsAuthenticated]


class POFormulaGroupingDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = POFormulaGrouping.objects.all()
    serializer_class = POFormulaGroupingSerializer
    permission_classes = [permissions.IsAuthenticated]


class DataEntryList(generics.ListCreateAPIView):
    queryset = DataEntry.objects.all()
    serializer_class = DataEntrySerializer
    permission_classes = [permissions.IsAuthenticated]


class DataEntryDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = DataEntry.objects.all()
    serializer_class = DataEntrySerializer
    permission_classes = [permissions.IsAuthenticated]


class TemplateNameList(generics.ListCreateAPIView):
    queryset = TemplateName.objects.all()
    serializer_class = TemplateNameSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = TemplateNameFilter


class TemplateNameDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = TemplateName.objects.all()
    serializer_class = TemplateNameSerializer
    permission_classes = [permissions.IsAuthenticated]


class UnitLibraryList(generics.ListCreateAPIView):
    queryset = UnitLibrary.objects.all()
    serializer_class = UnitLibrarySerializer
    permission_classes = [permissions.IsAuthenticated]


class UnitLibraryDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = UnitLibrary.objects.all()
    serializer_class = UnitLibrarySerializer
    permission_classes = [permissions.IsAuthenticated]


class DescriptionLibraryList(generics.ListCreateAPIView):
    queryset = DescriptionLibrary.objects.all()
    serializer_class = DescriptionLibrarySerializer
    permission_classes = [permissions.IsAuthenticated]


class DescriptionLibraryDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = DescriptionLibrary.objects.all()
    serializer_class = DescriptionLibrarySerializer
    permission_classes = [permissions.IsAuthenticated]


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
