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
from sales.models.estimate import EstimateTemplate
from sales.serializers.catalog import CatalogImageSerializer
from sales.serializers.estimate import EstimateTemplateForFormattingSerializer, EstimateTemplateForInvoiceSerializer, POFormulaDataSerializer, POFormulaForInvoiceSerializer
from sales.serializers.proposal import ProposalTemplateSerializer, PriceComparisonSerializer, \
    ProposalFormattingTemplateSerializer, ProposalWritingSerializer, PriceComparisonCompactSerializer, \
    ProposalWritingCompactSerializer, ProposalTemplateHtmlCssSerializer, ProposalWritingDataSerializer


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


def update_order(ids, model):
    query_set = model.objects.filter(id__in=ids)
    for obj in query_set:
        try:
            obj.order = ids.index(obj.pk)
        except ValueError:
            pass
    model.objects.bulk_update(query_set, ['order'])
    return query_set


@api_view(['GET', 'PUT'])
@permission_classes([permissions.IsAuthenticated & ProposalPermissions])
def get_table_formatting(request, pk):
    """
    Update row and column on proposal formatting

    Parameters:

        formulas: list id
        estimates: list id

        show_fields: list str
    """
    data = {}
    if request.method == 'GET':
        proposal_writing = get_object_or_404(ProposalWriting.objects.all(), pk=pk)
        data['formulas'] = ProposalWritingDataSerializer(proposal_writing).data
        data['show_writing_fields'] = proposal_writing.proposal_formatting.show_writing_fields
        data['show_estimate_fields'] = proposal_writing.proposal_formatting.show_estimate_fields

    if request.method == 'PUT':
        """Update order po formula"""
        proposal_writing = get_object_or_404(ProposalWriting.objects.all(), pk=pk)
        ids = request.data.get('formulas')
        estimate_ids = request.data.get('estimates')
        if ids:
            po_formulas = update_order(ids, POFormula)
            data['formulas'] = POFormulaDataSerializer(po_formulas.order_by('order'), context={'request': request}, many=True).data
        if estimate_ids:
            estimates = update_order(estimate_ids, EstimateTemplate)

        show_writing_fields = request.data.get('show_writing_fields')
        show_estimate_fields = request.data.get('show_estimate_fields')
        proposal_formatting = proposal_writing.proposal_formatting
        if show_writing_fields:
            proposal_formatting.show_writing_fields = show_writing_fields
        if show_estimate_fields:
            proposal_formatting.show_estimate_fields = show_estimate_fields
        proposal_formatting.save()
        data['show_writing_fields'] = show_writing_fields
        data['show_estimate_fields'] = show_estimate_fields

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
    """
    Get items for invoice
    """
    is_formula = request.GET.get('is_formula')
    proposal_writing = get_object_or_404(ProposalWriting.objects.all(), pk=pk)
    if not is_formula:
        estimate_templates = proposal_writing.get_estimates()
        data = EstimateTemplateForInvoiceSerializer(estimate_templates, context={'request': request}, many=True).data
    else:
        items = proposal_writing._get_poformula()
        data = POFormulaForInvoiceSerializer(items, context={'request': request}, many=True).data
    return Response(status=status.HTTP_200_OK, data=data)


@api_view(['GET', 'PUT'])
@permission_classes([permissions.IsAuthenticated & ProposalPermissions])
def proposal_formatting_view(request, pk):
    proposal_writing = get_object_or_404(ProposalWriting.objects.filter(company=get_request().user.company),
                                         pk=pk)
    all_writing_fields = ['id', 'name', 'linked_description', 'formula', 'quantity', 'markup', 'charge', 'material', 'unit',
                         'unit_price', 'cost', 'total_cost', 'gross_profit', 'description_of_formula', 'formula_scenario']
    all_estimate_fields = ['id', 'name', 'quantity', 'unit', 'total_charge']
    if request.method == 'GET':
        try:
            proposal_formatting = ProposalFormatting.objects.get(proposal_writing=proposal_writing)
        except ProposalFormatting.DoesNotExist:
            proposal_formatting = ProposalFormatting.objects.create(proposal_writing=proposal_writing)
        estimates = EstimateTemplateForFormattingSerializer(proposal_writing.get_estimates(), many=True).data
        serializer = ProposalFormattingTemplateSerializer(proposal_formatting, context={'request': request})
        return Response(status=status.HTTP_200_OK, data={**serializer.data,
                                                         **{'all_writing_fields': all_writing_fields,
                                                            'estimates': estimates,
                                                            'all_estimate_fields': all_estimate_fields}})

    if request.method == 'PUT':
        proposal_formatting = ProposalFormatting.objects.get(proposal_writing=proposal_writing)
        serializer = ProposalFormattingTemplateSerializer(proposal_formatting, data=request.data,
                                                          partial=True, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_200_OK, data={**serializer.data, **{'all_writing_fields': all_writing_fields,
                                                                               'all_estimate_fields': all_estimate_fields}})
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated & ProposalPermissions])
def reset_formatting(request, pk):
    proposal_writing = get_object_or_404(ProposalWriting.objects.filter(company=request.user.company), pk=pk)
    try:
        proposal_formatting = ProposalFormatting.objects.get(proposal_writing=proposal_writing)
        proposal_formatting.delete()
    except ProposalFormatting.DoesNotExist:
        pass
    return Response(status=status.HTTP_204_NO_CONTENT)


def view_proposal_formatting(request, formatting_id):
    try:
        data_proposal = ProposalFormatting.objects.get(id=formatting_id)
    except ProposalFormatting.DoesNotExist:
        raise Http404("ProposalFormatting does not exist")
    data_html = data_proposal.element
    return render(request, 'proposal_formatting.html', context={'javascript_code': data_html})


@api_view(['POST'])
def duplicate_proposal(request):
    """
    Payloads: {"proposal_id": [lead_id,..]}
    """
    proposal_ids = request.data.keys()
    objs = []
    for proposal_id in proposal_ids:
        for lead in request.data[proposal_id]:
            p = ProposalWriting.objects.get(pk=proposal_id)
            serializer = ProposalWritingSerializer(p).data
            dup = ProposalWritingSerializer(data=serializer, context={'request': request})
            dup.is_valid(raise_exception=True)
            objs.append(dup.save(lead_id=lead).id)
    serializer = ProposalWritingCompactSerializer(ProposalWriting.objects.filter(id__in=objs), many=True)
    return Response(status=status.HTTP_201_CREATED, data=serializer.data)
