from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, filters as rf_filters, status
from rest_framework.decorators import api_view, permission_classes
from django_filters import rest_framework as filters
from rest_framework.response import Response

from sales.filters.proposal import PriceComparisonFilter, ProposalWritingFilter, ProposalTemplateFilter
from sales.models import ProposalTemplate, PriceComparison, ProposalFormatting, ProposalWriting, GroupByEstimate
from sales.serializers.proposal import ProposalTemplateSerializer, PriceComparisonSerializer, \
    ProposalFormattingTemplateSerializer, ProposalWritingSerializer, PriceComparisonCompactSerializer, \
    ProposalWritingCompactSerializer, ProposalTemplateHtmlSerializer, ProposalTemplateHtmlCssSerializer
from api.middleware import get_request
from base.views.base import CompanyFilterMixin


class ProposalTemplateGenericView(generics.ListCreateAPIView, CompanyFilterMixin):
    queryset = ProposalTemplate.objects.all().prefetch_related('proposal_template_element__proposal_widget_element')
    serializer_class = ProposalTemplateSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = (filters.DjangoFilterBackend, rf_filters.SearchFilter)
    filterset_class = ProposalTemplateFilter
    search_fields = ('name',)


class ProposalTemplateDetailGenericView(generics.RetrieveUpdateDestroyAPIView):
    queryset = ProposalTemplate.objects.all().prefetch_related('proposal_template_element__proposal_widget_element')
    serializer_class = ProposalTemplateSerializer
    permission_classes = [permissions.IsAuthenticated]


class PriceComparisonList(generics.ListCreateAPIView, CompanyFilterMixin):
    queryset = PriceComparison.objects.all().order_by('-modified_date').prefetch_related('estimate_templates')
    serializer_class = PriceComparisonSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = (filters.DjangoFilterBackend, rf_filters.SearchFilter)
    filterset_class = PriceComparisonFilter
    search_fields = ('name',)


class PriceComparisonCompactList(generics.ListAPIView, CompanyFilterMixin):
    queryset = PriceComparison.objects.all().order_by('-modified_date').prefetch_related('estimate_templates')
    serializer_class = PriceComparisonCompactSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = (filters.DjangoFilterBackend, rf_filters.SearchFilter)
    filterset_class = PriceComparisonFilter
    search_fields = ('name',)


class PriceComparisonDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = PriceComparison.objects.all()
    serializer_class = PriceComparisonSerializer
    permission_classes = [permissions.IsAuthenticated]


class ProposalWritingList(generics.ListCreateAPIView, CompanyFilterMixin):
    queryset = ProposalWriting.objects.all().order_by('-modified_date').prefetch_related('writing_groups')
    serializer_class = ProposalWritingSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = (filters.DjangoFilterBackend, rf_filters.SearchFilter)
    filterset_class = ProposalWritingFilter
    search_fields = ('name',)


class ProposalWritingCompactList(generics.ListAPIView, CompanyFilterMixin):
    queryset = ProposalWriting.objects.all().order_by('-modified_date').prefetch_related('writing_groups')
    serializer_class = ProposalWritingCompactSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = (filters.DjangoFilterBackend, rf_filters.SearchFilter)
    filterset_class = ProposalWritingFilter
    search_fields = ('name',)


class ProposalWritingDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = ProposalWriting.objects.all()
    serializer_class = ProposalWritingSerializer
    permission_classes = [permissions.IsAuthenticated]


class ProposalFormattingTemplateGenericView(generics.ListCreateAPIView, CompanyFilterMixin):
    queryset = ProposalFormatting.objects.all()
    serializer_class = ProposalFormattingTemplateSerializer
    permission_classes = [permissions.IsAuthenticated]


class ProposalFormattingTemplateDetailGenericView(generics.RetrieveUpdateDestroyAPIView):
    queryset = ProposalFormatting.objects.all()
    serializer_class = ProposalFormattingTemplateSerializer
    permission_classes = [permissions.IsAuthenticated]


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_html_css_by_template(request, *args, **kwargs):
    pk = kwargs.get('pk')
    get_object_or_404(ProposalTemplate.objects.all(), pk=pk)
    template = ProposalTemplate.objects.prefetch_related('proposal_template_element__proposal_widget_element').get(id=pk)
    data = ProposalTemplateHtmlCssSerializer(
        template, context={'request': request}).data
    return Response(status=status.HTTP_200_OK, data=data)
