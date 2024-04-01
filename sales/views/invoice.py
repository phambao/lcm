from django.shortcuts import get_object_or_404
from django.conf import settings
from django.template.loader import render_to_string
from django.apps import apps
from django.utils.crypto import get_random_string
from rest_framework import generics, permissions
from rest_framework import status, filters as rf_filters
from rest_framework.response import Response
from rest_framework.decorators import api_view
from django_filters import rest_framework as filters

from api.models import InvoiceSetting
from base.permissions import InvoicePermissions
from base.serializers.config import CompanySerializer
from base.views.base import CompanyFilterMixin
from base.tasks import celery_send_mail
from sales.models import Invoice, PaymentHistory, LeadDetail, CreditMemo, InvoiceTemplate
from sales.models.invoice import TemplateInvoice
from sales.models.proposal import ProposalWriting
from sales.serializers.invoice import InvoiceSerializer, InvoiceTemplateMinorSerializer, PaymentHistorySerializer, InvoicePaymentSerializer, \
    ProposalForInvoiceSerializer, LeadInvoiceSerializer, CreditMemoSerializer, InvoiceTemplateSerializer
from sales.views.lead_list import LeadDetailList
from sales.views.proposal import ProposalWritingCompactList
from sales.filters.invoice import InvoiceFilter


class InvoiceListView(CompanyFilterMixin, generics.ListCreateAPIView):
    queryset = Invoice.objects.all()
    serializer_class = InvoiceSerializer
    permission_classes = [permissions.IsAuthenticated & InvoicePermissions]
    filter_backends = (filters.DjangoFilterBackend, rf_filters.SearchFilter)
    filterset_class = InvoiceFilter
    search_fields = ('name',)


class InvoicePaymentListView(CompanyFilterMixin, generics.ListAPIView):
    queryset = Invoice.objects.all()
    serializer_class = InvoicePaymentSerializer
    permission_classes = [permissions.IsAuthenticated & InvoicePermissions]


class InvoiceDetailGenericView(CompanyFilterMixin, generics.RetrieveUpdateDestroyAPIView):
    queryset = Invoice.objects.all()
    serializer_class = InvoiceSerializer
    permission_classes = [permissions.IsAuthenticated & InvoicePermissions]


class InvoiceProposal(ProposalWritingCompactList):
    serializer_class = ProposalForInvoiceSerializer


class InvoiceProposalDetail(generics.RetrieveAPIView):
    serializer_class = ProposalForInvoiceSerializer
    queryset = ProposalWriting.objects.all().order_by('-modified_date')
    permission_classes = [permissions.IsAuthenticated & InvoicePermissions]

class PaymentListView(CompanyFilterMixin, generics.ListCreateAPIView):
    queryset = PaymentHistory.objects.all()
    serializer_class = PaymentHistorySerializer
    permission_classes = [permissions.IsAuthenticated & InvoicePermissions]


class PaymentDetailView(CompanyFilterMixin, generics.RetrieveUpdateDestroyAPIView):
    queryset = PaymentHistory.objects.all()
    serializer_class = PaymentHistorySerializer
    permission_classes = [permissions.IsAuthenticated & InvoicePermissions]


class LeadInvoiceList(LeadDetailList):
    serializer_class = LeadInvoiceSerializer
    permission_classes = [permissions.IsAuthenticated & InvoicePermissions]
    queryset = LeadDetail.objects.all()


class CreditMemoList(CompanyFilterMixin, generics.ListCreateAPIView):
    serializer_class = CreditMemoSerializer
    permission_classes = [permissions.IsAuthenticated & InvoicePermissions]
    queryset = CreditMemo.objects.all()


class CreditMemoDetail(CompanyFilterMixin, generics.RetrieveUpdateDestroyAPIView):
    serializer_class = CreditMemoSerializer
    permission_classes = [permissions.IsAuthenticated & InvoicePermissions]
    queryset = CreditMemo.objects.all()


class InvoiceTemplateList(CompanyFilterMixin, generics.ListCreateAPIView):
    serializer_class = InvoiceTemplateSerializer
    permission_classes = [permissions.IsAuthenticated & InvoicePermissions]
    queryset = InvoiceTemplate.objects.all()


class InvoiceTemplateDetail(CompanyFilterMixin, generics.RetrieveUpdateDestroyAPIView):
    serializer_class = InvoiceTemplateSerializer
    permission_classes = [permissions.IsAuthenticated & InvoicePermissions]
    queryset = InvoiceTemplate.objects.all()


@api_view(['GET', 'PUT'])
def invoice_template_data(request, pk):
    invoice_obj = get_object_or_404(Invoice.objects.all(), pk=pk)
    company = invoice_obj.company

    template_obj, is_created = TemplateInvoice.objects.get_or_create(invoice=invoice_obj)
    if is_created:
        try:
            invoice_setting = InvoiceSetting.objects.get(company=company)
        except InvoiceSetting.DoesNotExist:
            invoice_setting = InvoiceSetting.objects.create(
                company=request.user.company,
                prefix='LCM',
                is_notify_internal_deadline=False,
                is_notify_owners_deadline=False,
                is_notify_owners_after_deadline=False,
                is_default_show=False,
                day_before=1,
                default_owners_invoice="default_owners_invoice"
            )
        template_obj.description = invoice_setting.default_owners_invoice
        template_obj.save()
    serializer = InvoiceTemplateMinorSerializer(template_obj)
    if request.method == 'PUT':
        serializer = InvoiceTemplateMinorSerializer(instance=template_obj, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
    company = invoice_obj.company
    company_data = CompanySerializer(company).data
    data = {
        'items': [{'name': 'name', 'description': 'description',
                   'quantity': 'quantity', 'total_price': '100', 'unit_price': '123'} for i in range(5)],
        'company': company_data,
        'invoice': InvoiceSerializer(invoice_obj).data
    }
    return Response(status=status.HTTP_201_CREATED, data={**data, **serializer.data})


Contact = apps.get_model('sales', 'Contact')


@api_view(['POST'])
def publish_template(request, pk):
    invoice_obj = get_object_or_404(Invoice.objects.all(), pk=pk)
    template_obj = invoice_obj.template
    serializer = InvoiceTemplateMinorSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    template_obj.printed = serializer.validated_data['printed']
    template_obj.save()
    contacts = Contact.objects.filter(id__in=template_obj.contacts).distinct()
    for contact in contacts:
        url = f'{settings.BASE_URL}{request.data["path"]}'
        if contact.pk == template_obj.primary_contact:
            url = url + f'?email={request.data["email"]}'
        content = render_to_string('proposal-formatting-sign.html', {'url': url, 'contact': contact})
        celery_send_mail.delay(f'Sign Electronically', content, settings.EMAIL_HOST_USER, [contact.email], False, html_message=content)
    return Response(status=status.HTTP_201_CREATED, data={'data': 'public success'})


@api_view(['POST', 'GET'])
def invoice_sign(request, pk):
    invoice = get_object_or_404(
        Invoice.objects.all(),
        pk=pk
    )
    invoice_template = invoice.template
    if request.method == 'GET':
        code = get_random_string(length=6, allowed_chars='1234567890')
        invoice_template.otp = code
        invoice_template.has_send_mail = True
        invoice_template.save()
        contact = Contact.objects.get(pk=invoice_template.primary_contact)
        content = render_to_string('proposal-formatting-sign-otp.html', {'otp': code, 'contact': contact})
        celery_send_mail.delay(f'Sign Electronically OTP', content, settings.EMAIL_HOST_USER,
                           [contact.email], False)
        return Response(status=status.HTTP_200_OK, data={'data': ' create code success'})

    if request.method == 'POST':
        otp = request.data['otp']
        signature = request.data['signature']
        if otp == invoice_template.otp:
            invoice_template.has_signed = True
            invoice_template.signature = signature
            invoice_template.save(update_fields=['has_signed', 'signature'])
            return Response(status=status.HTTP_200_OK, data={'data': 'Success'})
        else:
            return Response(status=status.HTTP_400_BAD_REQUEST, data={'data': 'Fail'})
