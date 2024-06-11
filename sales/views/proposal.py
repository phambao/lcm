import uuid

from django.conf import settings
from django.http import Http404
from django.shortcuts import get_object_or_404, render
from django.template.loader import render_to_string
from django.utils.crypto import get_random_string
from django_filters import rest_framework as filters
from django.apps import apps
from django.utils import timezone
from openpyxl.reader.excel import load_workbook
from rest_framework import generics, permissions, filters as rf_filters, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from api.middleware import get_request
from base.constants import DEFAULT_NOTE, INTRO
from base.permissions import ProposalPermissions
from base.serializers.config import CompanySerializer
from base.utils import file_response, pop
from base.views.base import CompanyFilterMixin
from base.tasks import celery_send_mail, export_proposal, send_mail_with_attachment
from sales.filters.proposal import PriceComparisonFilter, ProposalWritingFilter, ProposalTemplateFilter
from sales.models import ProposalTemplate, PriceComparison, ProposalFormatting, ProposalWriting, POFormula, \
    ProposalFormattingSign, ProposalSetting
from sales.models.estimate import EstimateTemplate
from sales.models.lead_list import ActivitiesLog
from sales.models.proposal import ProposalStatus
from sales.serializers.catalog import CatalogImageSerializer
from sales.serializers.estimate import EstimateTemplateForFormattingSerializer, EstimateTemplateForInvoiceSerializer, POFormulaDataSerializer, POFormulaForInvoiceSerializer
from sales.serializers.proposal import FormatEstimateSerializer, FormatFormulaSerializer, ProposalFormattingTemplateMinorSerializer, ProposalTemplateSerializer, PriceComparisonSerializer, \
    ProposalFormattingTemplateSerializer, ProposalWritingSerializer, PriceComparisonCompactSerializer, \
    ProposalWritingCompactSerializer, ProposalTemplateHtmlCssSerializer, ProposalWritingDataSerializer, \
    ProposalFormattingTemplateSignSerializer, ProposalFormattingTemplateSignsSerializer, ProposalSettingSerializer, WritingStatusSerializer
from sales.views.estimate import ALL_ESTIMATE_PREFETCH_RELATED


PROPOSAL_GROUP_PREFETCH_RELATED = ['estimate_templates__' + i for i in ALL_ESTIMATE_PREFETCH_RELATED]
PROPOSAL_PREFETCH_RELATED = ['writing_groups__' + i for i in PROPOSAL_GROUP_PREFETCH_RELATED]
PRICE_COMPARISION_PREFETCH_RELATED = ['groups__' + i for i in PROPOSAL_GROUP_PREFETCH_RELATED]


class ProposalTemplateGenericView(CompanyFilterMixin, generics.ListCreateAPIView):
    queryset = ProposalTemplate.objects.all().prefetch_related('proposal_template_element__proposal_widget_element')
    serializer_class = ProposalTemplateSerializer
    permission_classes = [permissions.IsAuthenticated & ProposalPermissions]
    filter_backends = (filters.DjangoFilterBackend, rf_filters.SearchFilter, rf_filters.OrderingFilter)
    ordering_fields = ['is_default',]
    filterset_class = ProposalTemplateFilter
    search_fields = ('name',)


class ProposalTemplateDetailGenericView(generics.RetrieveUpdateDestroyAPIView):
    queryset = ProposalTemplate.objects.all().prefetch_related('proposal_template_element__proposal_widget_element')
    serializer_class = ProposalTemplateSerializer
    permission_classes = [permissions.IsAuthenticated & ProposalPermissions]


class PriceComparisonList(CompanyFilterMixin, generics.ListCreateAPIView):
    queryset = PriceComparison.objects.all().order_by('-modified_date').prefetch_related(*PRICE_COMPARISION_PREFETCH_RELATED)
    serializer_class = PriceComparisonSerializer
    permission_classes = [permissions.IsAuthenticated & ProposalPermissions]
    filter_backends = (filters.DjangoFilterBackend, rf_filters.SearchFilter)
    filterset_class = PriceComparisonFilter
    search_fields = ('name',)


class PriceComparisonCompactList(CompanyFilterMixin, generics.ListAPIView):
    queryset = PriceComparison.objects.all().order_by('-modified_date').prefetch_related(*PRICE_COMPARISION_PREFETCH_RELATED)
    serializer_class = PriceComparisonCompactSerializer
    permission_classes = [permissions.IsAuthenticated & ProposalPermissions]
    filter_backends = (filters.DjangoFilterBackend, rf_filters.SearchFilter)
    filterset_class = PriceComparisonFilter
    search_fields = ('name',)


class PriceComparisonDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = PriceComparison.objects.all().prefetch_related(*PRICE_COMPARISION_PREFETCH_RELATED)
    serializer_class = PriceComparisonSerializer
    permission_classes = [permissions.IsAuthenticated & ProposalPermissions]


class ProposalWritingList(CompanyFilterMixin, generics.ListCreateAPIView):
    queryset = ProposalWriting.objects.filter(is_show=True).order_by('-modified_date').prefetch_related(*PROPOSAL_PREFETCH_RELATED)
    serializer_class = ProposalWritingSerializer
    permission_classes = [permissions.IsAuthenticated & ProposalPermissions]
    filter_backends = (filters.DjangoFilterBackend, rf_filters.SearchFilter)
    filterset_class = ProposalWritingFilter
    search_fields = ('name',)


class ProposalWritingCompactList(CompanyFilterMixin, generics.ListAPIView):
    queryset = ProposalWriting.objects.filter(is_show=True).order_by('-modified_date').prefetch_related(*PROPOSAL_PREFETCH_RELATED)
    serializer_class = ProposalWritingCompactSerializer
    permission_classes = [permissions.IsAuthenticated & ProposalPermissions]
    filter_backends = (filters.DjangoFilterBackend, rf_filters.SearchFilter)
    filterset_class = ProposalWritingFilter
    search_fields = ('name',)


class ProposalWritingDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = ProposalWriting.objects.all().prefetch_related(*PROPOSAL_PREFETCH_RELATED)
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


class ProposalFormattingTemplateSignDetailGenericView(generics.RetrieveUpdateDestroyAPIView):
    queryset = ProposalFormattingSign.objects.all()
    serializer_class = ProposalFormattingTemplateSignSerializer


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
    is_formula = request.GET.get('is_formula', 'true')
    proposal_writing = get_object_or_404(ProposalWriting.objects.all(), pk=pk)
    if is_formula != 'true':
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
    all_writing_fields = ['id', 'name', 'linked_description', 'formula', 'quantity', 'markup', 'charge', 'unit',
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


@api_view(['GET', 'PUT'])
def proposal_formatting_v2_view(request, pk):
    proposal_writing = get_object_or_404(ProposalWriting.objects.all(), pk=pk)
    all_formula_fields = ['id', 'name', 'linked_description', 'formula', 'quantity', 'markup', 'charge', 'material', 'unit',
                         'unit_price', 'cost', 'total_cost', 'gross_profit', 'description_of_formula', 'formula_scenario']
    company = proposal_writing.company
    try:
        proposal_setting = ProposalSetting.objects.get(company=company)
    except ProposalSetting.DoesNotExist:
        proposal_setting = ProposalSetting.objects.create(
            company=company,
            intro=INTRO,
            default_note=DEFAULT_NOTE,
            pdf_file=''
        )
    company_data = CompanySerializer(company).data
    all_format_fields = ['id', 'name', 'description', 'unit', 'quantity', 'total_price', 'unit_price']
    data = {'all_format_fields': all_format_fields, 'company': company_data,
            'all_formula_fields': all_formula_fields,
            'status': proposal_writing.status,
            'proposal_setting': ProposalSettingSerializer(proposal_setting).data}
    if request.method == 'GET':
        try:
            proposal_formatting = ProposalFormatting.objects.get(proposal_writing=proposal_writing)
        except ProposalFormatting.DoesNotExist:
            proposal_formatting = ProposalFormatting.objects.create(proposal_writing=proposal_writing)
        serializer = ProposalFormattingTemplateMinorSerializer(proposal_formatting, context={'request': request})
        return Response(status=status.HTTP_200_OK, data={**serializer.data, **data})

    if request.method == 'PUT':
        proposal_formatting = ProposalFormatting.objects.get(proposal_writing=proposal_writing)
        estimate_params = request.data.get('estimates', [])
        formula_params = request.data.get('formulas', [])
        query_set = EstimateTemplate.objects.filter(id__in=estimate_params)
        for obj in query_set:
            try:
                obj.format_order = estimate_params.index(obj.pk)
            except ValueError:
                pass
        EstimateTemplate.objects.bulk_update(query_set, ['format_order'])

        query_set = POFormula.objects.filter(id__in=formula_params)
        for obj in query_set:
            try:
                obj.order = formula_params.index(obj.pk)
            except ValueError:
                pass
        POFormula.objects.bulk_update(query_set, ['order'])

        serializer = ProposalFormattingTemplateMinorSerializer(proposal_formatting, data=request.data, context={'request': request})
        serializer.is_valid()
        serializer.save()
        return Response(status=status.HTTP_200_OK, data={**serializer.data, **data})
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

from datetime import datetime
@api_view(['POST'])
def duplicate_proposal(request):
    """
    Payloads: {"proposal_id": [lead_id,..]}
    """
    try:
        name = request.data.pop('name')
    except KeyError:
        name = ''

    if not name:
        return Response(status=status.HTTP_400_BAD_REQUEST, data={"name": ["This field is required"]})
    proposal_ids = request.data.keys()
    objs = []
    for proposal_id in proposal_ids:
        for lead in request.data[proposal_id]:
            p = ProposalWriting.objects.get(pk=proposal_id)
            serializer = ProposalWritingSerializer(p, context={'request': request}).data
            temp = []
            for contact in serializer['proposal_formatting']['contacts']:
                temp.append(contact['id'])

            serializer['proposal_formatting']['contacts'] = temp
            dup = ProposalWritingSerializer(data=serializer, context={'request': request})
            dup.is_valid(raise_exception=True)
            objs.append(dup.save(lead_id=lead, name=name).id)
    serializer = ProposalWritingCompactSerializer(ProposalWriting.objects.filter(id__in=objs),
                                                  many=True, context={'request': request})

    return Response(status=status.HTTP_201_CREATED, data=serializer.data)


Contact = apps.get_model('sales', 'Contact')


@api_view(['POST'])
def proposal_formatting_public(request, pk):
    proposal_writing = get_object_or_404(ProposalWriting.objects.all(), pk=pk)
    contacts = Contact.objects.filter(id__in=proposal_writing.proposal_formatting.contacts).distinct()
    if not contacts:
        return Response(status=status.HTTP_400_BAD_REQUEST, data={'message': 'No contact'})
    proposal_template = ProposalFormatting.objects.get_or_create(proposal_writing=proposal_writing)[0]
    serializer = ProposalFormattingTemplateMinorSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    proposal_template.print_date = serializer.validated_data['print_date']
    proposal_template.has_send_mail = True
    proposal_template.sign_date = None
    proposal_template.signature = ''
    proposal_template.save()
    proposal_writing.status = 'sent'
    proposal_writing.save(update_fields=['status'])
    ActivitiesLog.objects.create(lead=proposal_writing.lead, status='sent', type_id=proposal_writing.pk,
                                 title=f'{proposal_writing.name}', type='proposal', start_date=timezone.now())
    for contact in contacts:
        url = f'{settings.BASE_URL}{request.data["path"]}'
        if contact.pk == proposal_writing.proposal_formatting.primary_contact:
            url = url + f'?email={request.data["email"]}'
        content = render_to_string('proposal-formatting-sign.html', {'url': url, 'contact': contact})
        celery_send_mail.delay(f'Sign Electronically', content, settings.EMAIL_HOST_USER, [contact.email], False, html_message=content)
    return Response(status=status.HTTP_201_CREATED, data={'data': 'public success'})


@api_view(['POST', 'GET'])
def proposal_sign(request, pk):
    proposal_writing = get_object_or_404(
        ProposalWriting.objects.all(),
        pk=pk
    )
    proposal_template = proposal_writing.proposal_formatting
    if request.method == 'GET':
        code = get_random_string(length=6, allowed_chars='1234567890')
        proposal_template.otp = code
        proposal_template.has_send_mail = True
        proposal_template.save()
        contact = Contact.objects.get(pk=proposal_template.primary_contact)
        content = render_to_string('proposal-formatting-sign-otp.html', {'otp': code, 'contact': contact})
        celery_send_mail.delay(f'Sign Electronically OTP', content, settings.EMAIL_HOST_USER,
                           [contact.email], False)
        return Response(status=status.HTTP_200_OK, data={'data': ' create code success'})

    if request.method == 'POST':
        otp = request.data['otp']
        signature = request.data['signature']
        if otp == proposal_template.otp or not proposal_template.is_sent_otp:
            proposal_template.has_signed = True
            proposal_template.signature = signature
            proposal_template.sign_date = timezone.now()
            proposal_template.save(update_fields=['has_signed', 'signature', 'sign_date'])
            proposal_writing.status = 'approved'
            proposal_writing.save(update_fields=['status'])
            ActivitiesLog.objects.create(lead=proposal_writing.lead, status='approved', type_id=proposal_writing.pk,
                                         title=f'{proposal_writing.name}', type='proposal', start_date=proposal_template.sign_date)

            files = request.data.getlist('file')
            contact = Contact.objects.get(pk=proposal_template.primary_contact)
            content = render_to_string('proposal-formatting-sign-otp-success.html', {'contact': contact})
            send_mail_with_attachment(f'Sign Electronically OTP', content, settings.EMAIL_HOST_USER,
                                      [contact.email], files)
            return Response(status=status.HTTP_200_OK, data={'data': 'Success'})
        else:
            return Response(status=status.HTTP_400_BAD_REQUEST, data={'data': 'Fail'})


@api_view(['POST'])
def create_code_proposal_formatting_sign(request):
    data = request.data
    pk = data.get('id')
    email = data.get('email')
    code = get_random_string(length=6, allowed_chars='1234567890')
    proposal_sign = ProposalFormattingSign.objects.get(id=pk)
    proposal_sign.code = code
    proposal_sign.save()
    content = render_to_string('proposal-formatting-sign-otp.html', {'otp': code})
    celery_send_mail.delay(f'Sign Electronically OTP', content, settings.EMAIL_HOST_USER,
                           [email], False)

    return Response(status=status.HTTP_200_OK, data={'data': ' create code success'})


@api_view(['POST'])
def check_code_proposal_formatting_sign(request):
    """
    Payloads: {"id": "1" , "code":"123456"}
    """
    data = request.data
    pk = data.get('id')
    code = data.get('code')
    p = ProposalFormattingSign.objects.get(pk=pk)
    if p.code == code:
        return Response(status=status.HTTP_200_OK, data={'data': 'code success'})
    else:
        return Response(status=status.HTTP_400_BAD_REQUEST, data={'data': 'code error'})


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated & ProposalPermissions])
def export_proposal_view(request):
    user_id = request.user.id
    process_export = export_proposal.delay(list_proposal=request.GET.getlist('pk'), user_id=user_id)
    task_id = process_export.id

    return Response(status=status.HTTP_200_OK, data={"task_id": task_id})


@api_view(['GET', 'PUT'])
@permission_classes([permissions.IsAuthenticated & ProposalPermissions])
def proposal_setting_field(request):

    try:
        proposal_setting = ProposalSetting.objects.get(company=request.user.company)
    except ProposalSetting.DoesNotExist:
        proposal_setting = ProposalSetting.objects.create(
            company=request.user.company,
            intro=INTRO,
            default_note=DEFAULT_NOTE,
            pdf_file=''
        )
    if request.method == 'GET':
        serializer = ProposalSettingSerializer(proposal_setting)
        return Response(status=status.HTTP_200_OK, data=serializer.data)

    if request.method == 'PUT':
        serializer = ProposalSettingSerializer(proposal_setting, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_200_OK, data=serializer.data)
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['GET', 'PUT'])
@permission_classes([permissions.IsAuthenticated & ProposalPermissions])
def status_writing(request, pk):
    proposal_writing = get_object_or_404(ProposalWriting.objects.all(), pk=pk)
    if request.method == 'PUT':
        serializer = WritingStatusSerializer(instance=proposal_writing, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        ActivitiesLog.objects.create(lead=proposal_writing.lead, status='approved', type_id=proposal_writing.pk,
                                     title=f'{proposal_writing.name}', type='proposal', start_date=timezone.now())
    status = proposal_writing.status
    return Response(status=200, data={'status': status})


@api_view(['PUT'])
@permission_classes([permissions.IsAuthenticated & ProposalPermissions])
def reset_signature(request, pk):
    proposal_writing = get_object_or_404(ProposalWriting.objects.all(), pk=pk)
    proposal_writing.reset_formatting()
    proposal_writing.status = 'draft'
    proposal_writing.save()
    return Response(status=200)


def get_data_template_group(estimates, tab):
    template_groups = []
    for estimate in estimates:
        estimate.get_info()
        estimate_data = FormatEstimateSerializer(estimate).data
        del estimate_data['formulas']
        estimate_data['section'] = tab
        estimate_data['is_formula'] = False
        template_groups.append(estimate_data)
    return template_groups


def get_data(type, items):
    return {'name': 'Unassigned', 'id': uuid.uuid4(), 'type': type, 'can_edit': False, 'items': items}


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated & ProposalPermissions])
def parse_template(request):
    #  Get Proposal Serializer
    data = request.data
    data['name'] = 'Template'
    serializer = ProposalWritingSerializer(data=request.data, context={'request': request})
    serializer.is_valid(raise_exception=True)
    proposal_writing = serializer.save(is_show=False)
    template_groups = {'estimates': {'General': [], 'Optional Add-on Services': [], 'Additional Costs': []},
                       'formulas': {'General': [], 'Optional Add-on Services': [], 'Additional Costs': []}}
    #  Get Proposal Formatting
    general_estimates = proposal_writing.get_estimates(type=0)
    template_groups['estimates']['General'].append(get_data('estimates', get_data_template_group(general_estimates, 'General')))
    general_items = FormatFormulaSerializer(proposal_writing.get_formulas(0), many=True).data
    template_groups['formulas']['General'].append(get_data('formulas', general_items))

    add_on_estimates = proposal_writing.get_estimates(type=1)
    template_groups['estimates']['Optional Add-on Services'].append(
        get_data('estimates', get_data_template_group(add_on_estimates, 'Optional Add-on Services'))
    )
    service_items = FormatFormulaSerializer(proposal_writing.get_formulas(1), many=True).data
    template_groups['formulas']['Optional Add-on Services'].append(get_data('formulas', service_items))

    additional_estimates = proposal_writing.get_estimates(type=2)
    template_groups['estimates']['Additional Costs'].append(get_data('estimates', get_data_template_group(additional_estimates, 'Additional Costs')))
    addon_items = FormatFormulaSerializer(proposal_writing.get_formulas(2), many=True).data
    template_groups['formulas']['Additional Costs'].append(get_data('formulas', addon_items))

    for formula in general_items:
        if formula['catalog_name']:
            template_groups[formula['catalog_name']] = {
                'General': [{'name': 'Unassigned', 'id': uuid.uuid4(), 'type': 'formulas', 'items': []}],
                'Optional Add-on Services': [{'name': 'Unassigned', 'id': uuid.uuid4(), 'type': 'formulas', 'items': []}],
                'Additional Costs': [{'name': 'Unassigned', 'id': uuid.uuid4(), 'type': 'formulas', 'items': []}]}
    for formula in service_items:
        if formula['catalog_name']:
            template_groups[formula['catalog_name']] = {
                'General': [{'name': 'Unassigned', 'id': uuid.uuid4(), 'type': 'formulas', 'items': []}],
                'Optional Add-on Services': [{'name': 'Unassigned', 'id': uuid.uuid4(), 'type': 'formulas', 'items': []}],
                'Additional Costs': [{'name': 'Unassigned', 'id': uuid.uuid4(), 'type': 'formulas', 'items': []}]}
    for formula in addon_items:
        if formula['catalog_name']:
            template_groups[formula['catalog_name']] = {
                'General': [{'name': 'Unassigned', 'id': uuid.uuid4(), 'type': 'formulas', 'items': []}],
                'Optional Add-on Services': [{'name': 'Unassigned', 'id': uuid.uuid4(), 'type': 'formulas', 'items': []}],
                'Additional Costs': [{'name': 'Unassigned', 'id': uuid.uuid4(), 'type': 'formulas', 'items': []}]}

    for formula in general_items:
        if formula['catalog_name']:
            template_groups[formula['catalog_name']]['General'][0]['items'].append(formula)
    for formula in service_items:
        if formula['catalog_name']:
            template_groups[formula['catalog_name']]['Optional Add-on Services'][0]['items'].append(formula)
    for formula in addon_items:
        if formula['catalog_name']:
            template_groups[formula['catalog_name']]['Additional Costs'][0]['items'].append(formula)
    proposal_writing.delete()
    return Response(status=status.HTTP_200_OK, data=template_groups)
