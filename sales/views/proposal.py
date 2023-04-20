from rest_framework import generics, permissions

from sales.models import ProposalTemplate, PriceComparison, ProposalFormatting
from sales.serializers.proposal import ProposalTemplateSerializer, PriceComparisonSerializer, \
    ProposalFormattingTemplateSerializer


class ProposalTemplateGenericView(generics.ListCreateAPIView):
    queryset = ProposalTemplate.objects.all().prefetch_related('proposal_template_element__proposal_widget_element')
    serializer_class = ProposalTemplateSerializer
    permission_classes = [permissions.IsAuthenticated]
    # filter_backends = (filters.DjangoFilterBackend, rf_filters.SearchFilter)
    # filterset_class = ToDoFilter


class ProposalTemplateDetailGenericView(generics.RetrieveUpdateDestroyAPIView):
    queryset = ProposalTemplate.objects.all().prefetch_related('proposal_template_element__proposal_widget_element')
    serializer_class = ProposalTemplateSerializer
    permission_classes = [permissions.IsAuthenticated]


class PriceComparisonList(generics.ListCreateAPIView):
    queryset = PriceComparison.objects.all()
    serializer_class = PriceComparisonSerializer
    permission_classes = [permissions.IsAuthenticated]


class PriceComparisonDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = PriceComparison.objects.all()
    serializer_class = PriceComparisonSerializer
    permission_classes = [permissions.IsAuthenticated]


class ProposalFormattingTemplateGenericView(generics.ListCreateAPIView):
    queryset = ProposalFormatting.objects.all()
    serializer_class = ProposalFormattingTemplateSerializer
    permission_classes = [permissions.IsAuthenticated]


class ProposalFormattingTemplateDetailGenericView(generics.RetrieveUpdateDestroyAPIView):
    queryset = ProposalFormatting.objects.all()
    serializer_class = ProposalFormattingTemplateSerializer
    permission_classes = [permissions.IsAuthenticated]