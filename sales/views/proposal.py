from django.http import Http404
from django.shortcuts import get_object_or_404, render
from django_filters import rest_framework as filters
from rest_framework import generics, permissions, filters as rf_filters, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from api.middleware import get_request
from base.permissions import ProposalPermissions
from base.views.base import CompanyFilterMixin
from sales.filters.proposal import PriceComparisonFilter, ProposalWritingFilter, ProposalTemplateFilter
from sales.models import ProposalTemplate, PriceComparison, ProposalFormatting, ProposalWriting, POFormula
from sales.serializers.catalog import CatalogImageSerializer
from sales.serializers.estimate import POFormulaDataSerializer
from sales.serializers.proposal import ProposalTemplateSerializer, PriceComparisonSerializer, \
    ProposalFormattingTemplateSerializer, ProposalWritingSerializer, PriceComparisonCompactSerializer, \
    ProposalWritingCompactSerializer, ProposalTemplateHtmlCssSerializer


class ProposalTemplateGenericView(CompanyFilterMixin, generics.ListCreateAPIView):
    queryset = ProposalTemplate.objects.all().prefetch_related('proposal_template_element__proposal_widget_element')
    serializer_class = ProposalTemplateSerializer
    permission_classes = [permissions.IsAuthenticated & ProposalPermissions]
    filter_backends = (filters.DjangoFilterBackend, rf_filters.SearchFilter)
    filterset_class = ProposalTemplateFilter
    search_fields = ('name',)


class ProposalTemplateDetailGenericView(generics.RetrieveUpdateDestroyAPIView):
    queryset = ProposalTemplate.objects.all().prefetch_related('proposal_template_element__proposal_widget_element')
    serializer_class = ProposalTemplateSerializer
    permission_classes = [permissions.IsAuthenticated & ProposalPermissions]


class PriceComparisonList(CompanyFilterMixin, generics.ListCreateAPIView):
    queryset = PriceComparison.objects.all().order_by('-modified_date').prefetch_related('groups')
    serializer_class = PriceComparisonSerializer
    permission_classes = [permissions.IsAuthenticated & ProposalPermissions]
    filter_backends = (filters.DjangoFilterBackend, rf_filters.SearchFilter)
    filterset_class = PriceComparisonFilter
    search_fields = ('name',)


class PriceComparisonCompactList(CompanyFilterMixin, generics.ListAPIView):
    queryset = PriceComparison.objects.all().order_by('-modified_date').prefetch_related('groups')
    serializer_class = PriceComparisonCompactSerializer
    permission_classes = [permissions.IsAuthenticated & ProposalPermissions]
    filter_backends = (filters.DjangoFilterBackend, rf_filters.SearchFilter)
    filterset_class = PriceComparisonFilter
    search_fields = ('name',)


class PriceComparisonDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = PriceComparison.objects.all()
    serializer_class = PriceComparisonSerializer
    permission_classes = [permissions.IsAuthenticated & ProposalPermissions]


class ProposalWritingList(CompanyFilterMixin, generics.ListCreateAPIView):
    queryset = ProposalWriting.objects.all().order_by('-modified_date').prefetch_related('writing_groups')
    serializer_class = ProposalWritingSerializer
    permission_classes = [permissions.IsAuthenticated & ProposalPermissions]
    filter_backends = (filters.DjangoFilterBackend, rf_filters.SearchFilter)
    filterset_class = ProposalWritingFilter
    search_fields = ('name',)


class ProposalWritingCompactList(CompanyFilterMixin, generics.ListAPIView):
    queryset = ProposalWriting.objects.all().order_by('-modified_date').prefetch_related('writing_groups')
    serializer_class = ProposalWritingCompactSerializer
    permission_classes = [permissions.IsAuthenticated & ProposalPermissions]
    filter_backends = (filters.DjangoFilterBackend, rf_filters.SearchFilter)
    filterset_class = ProposalWritingFilter
    search_fields = ('name',)


class ProposalWritingDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = ProposalWriting.objects.all()
    serializer_class = ProposalWritingSerializer
    permission_classes = [permissions.IsAuthenticated & ProposalPermissions]


class ProposalFormattingTemplateGenericView(CompanyFilterMixin, generics.ListCreateAPIView):
    queryset = ProposalFormatting.objects.all()
    serializer_class = ProposalFormattingTemplateSerializer
    permission_classes = [permissions.IsAuthenticated & ProposalPermissions]


class ProposalFormattingTemplateDetailGenericView(generics.RetrieveUpdateDestroyAPIView):
    queryset = ProposalFormatting.objects.all()
    serializer_class = ProposalFormattingTemplateSerializer
    permission_classes = [permissions.IsAuthenticated & ProposalPermissions]

    def get_queryset(self):
        proposal_writing = get_object_or_404(ProposalWriting.objects.filter(company=get_request().user.company),
                                             pk=self.kwargs['pk'])
        proposal_formatting = proposal_writing.proposal_formatting
        if not proposal_formatting:
            proposal_formatting = ProposalFormatting.objects.create(proposal_writing=proposal_writing)
        return ProposalFormatting.objects.all()


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated & ProposalPermissions])
def get_html_css_by_template(request, *args, **kwargs):
    pk = kwargs.get('pk')
    get_object_or_404(ProposalTemplate.objects.all(), pk=pk)
    template = ProposalTemplate.objects.prefetch_related('proposal_template_element__proposal_widget_element').get(id=pk)
    data = ProposalTemplateHtmlCssSerializer(
        template, context={'request': request}).data
    return Response(status=status.HTTP_200_OK, data=data)


@api_view(['GET', 'PUT'])
@permission_classes([permissions.IsAuthenticated & ProposalPermissions])
def get_data(request, pk):
    if request.method == 'GET':
        proposal_writing = get_object_or_404(ProposalWriting.objects.all(), pk=pk)
        po_formulas = proposal_writing.get_data_formula().order_by('order')
        data = POFormulaDataSerializer(po_formulas, context={'request': request}, many=True).data

    if request.method == 'PUT':
        """Update order po formula"""
        ids = request.data
        po_formulas = POFormula.objects.filter(id__in=ids)
        for po_formula in po_formulas:
            try:
                po_formula.order = ids.index(po_formula.pk)
            except ValueError:
                pass
        POFormula.objects.bulk_update(po_formulas, ['order'])
        data = POFormulaDataSerializer(po_formulas.order_by('order'), context={'request': request}, many=True).data

    return Response(status=status.HTTP_200_OK, data=data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated & ProposalPermissions])
def get_image(request, pk):
    proposal_writing = get_object_or_404(ProposalWriting.objects.all(), pk=pk)
    imgs = proposal_writing.get_imgs()
    data = CatalogImageSerializer(imgs, context={'request': request}, many=True).data
    return Response(status=status.HTTP_200_OK, data=data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated & ProposalPermissions])
def get_items(request, pk):
    proposal_writing = get_object_or_404(ProposalWriting.objects.all(), pk=pk)
    items = proposal_writing._get_poformula()
    data = POFormulaDataSerializer(items, context={'request': request}, many=True).data
    return Response(status=status.HTTP_200_OK, data=data)


@api_view(['GET', 'PUT'])
@permission_classes([permissions.IsAuthenticated & ProposalPermissions])
def proposal_formatting_view(request, pk):
    proposal_writing = get_object_or_404(ProposalWriting.objects.filter(company=get_request().user.company),
                                         pk=pk)
    all_fields = ['id', 'name', 'linked_description', 'formula', 'quantity', 'markup', 'charge', 'material', 'unit',
                  'unit_price', 'cost', 'total_cost', 'gross_profit', 'description_of_formula', 'formula_scenario',
                  'material_data_entry']
    if request.method == 'GET':
        try:
            proposal_formatting = ProposalFormatting.objects.get(proposal_writing=proposal_writing)
        except ProposalFormatting.DoesNotExist:
            proposal_formatting = ProposalFormatting.objects.create(proposal_writing=proposal_writing)
        serializer = ProposalFormattingTemplateSerializer(proposal_formatting, context={'request': request})
        return Response(status=status.HTTP_200_OK, data={**serializer.data, **{'all_fields': all_fields}})

    if request.method == 'PUT':
        proposal_formatting = ProposalFormatting.objects.get(proposal_writing=proposal_writing)
        serializer = ProposalFormattingTemplateSerializer(proposal_formatting, data=request.data,
                                                          partial=True, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_200_OK, data={**serializer.data, **{'all_fields': all_fields}})
    return Response(status=status.HTTP_204_NO_CONTENT)


def view_proposal_formatting(request, formatting_id):
    try:
        data_proposal = ProposalFormatting.objects.get(id=formatting_id)
    except ProposalFormatting.DoesNotExist:
        raise Http404("ProposalFormatting does not exist")
    data_html = data_proposal.element
    return render(request, 'proposal_formatting.html', context={'javascript_code': data_html})

