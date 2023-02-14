from rest_framework import generics, permissions
from django_filters import rest_framework as filters

from sales.filters.estimate import TemplateNameFilter
from sales.models.estimate import POFormula, POFormulaGrouping, DataEntry, TemplateName
from sales.serializers.estimate import POFormulaSerializer, POFormulaGroupingSerializer, DataEntrySerializer, \
    TemplateNameSerializer


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
