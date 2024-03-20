from datetime import datetime
from datetime import timedelta
import json

from django.utils.timezone import now
from django.apps import apps
from django.db.models import Value, Q, Subquery
from django_filters.filters import _truncate
from openpyxl import Workbook, load_workbook
from rest_framework import generics, permissions, status, filters as rf_filters
from django_filters import rest_framework as filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.generics import get_object_or_404
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response
from rest_framework import serializers

from base.permissions import EstimatePermissions
from base.utils import file_response
from sales.filters.estimate import FormulaFilter, EstimateTemplateFilter, AssembleFilter, GroupFormulaFilter,\
    DescriptionFilter, UnitFilter, DataEntryFilter
from sales.models import DataPoint, Catalog
from sales.models.estimate import POFormula, POFormulaGrouping, DataEntry, POFormulaToDataEntry, UnitLibrary, \
    DescriptionLibrary, Assemble, EstimateTemplate, MaterialView
from sales.serializers.catalog import CatalogEstimateSerializer, CatalogEstimateWithParentSerializer, CatalogLevelValueSerializer
from sales.serializers.estimate import POFormulaGroupCompactSerializer, POFormulaSerializer, POFormulaGroupingSerializer, DataEntrySerializer, \
    UnitLibrarySerializer, DescriptionLibrarySerializer, LinkedDescriptionSerializer, AssembleSerializer, \
    EstimateTemplateSerializer, TaggingSerializer, GroupFormulasSerializer, POFormulaCompactSerializer, \
    AssembleCompactSerializer, EstimateTemplateCompactSerializer
from sales.views.catalog import parse_c_table
from api.middleware import get_request
from base.views.base import CompanyFilterMixin
from base.constants import null, true, false

DATA_ENTRY_PREFETCH_RELATED = ['data_entry__unit', 'data_entry__material_selections', 'data_entry']
FORMULA_PREFETCH_RELATED = ['self_data_entries__' + i for i in DATA_ENTRY_PREFETCH_RELATED]
GROUP_PREFETCH_RELATED = ['group_formulas__' + i for i in FORMULA_PREFETCH_RELATED]
ASSEMBLE_PREFETCH_RELATED = ['assemble_formulas__' + i for i in FORMULA_PREFETCH_RELATED]
ESTIMATE_PREFETCH_RELATED = ['assembles__' + i for i in ASSEMBLE_PREFETCH_RELATED]
ESTIMATE_DATA_ENTRY_PREFETCH_RELATED = ['data_entries__' + i for i in DATA_ENTRY_PREFETCH_RELATED]
MATERIAL_PREFETCH_RELATED = ['material_views__' + i for i in DATA_ENTRY_PREFETCH_RELATED]
ALL_ESTIMATE_PREFETCH_RELATED = [*ESTIMATE_PREFETCH_RELATED, *MATERIAL_PREFETCH_RELATED,
                                 *ESTIMATE_DATA_ENTRY_PREFETCH_RELATED, 'data_views', 'data_views__unit']


class POFormulaList(CompanyFilterMixin, generics.ListCreateAPIView):
    queryset = POFormula.objects.filter(is_show=True, group=None).\
        prefetch_related(*FORMULA_PREFETCH_RELATED).select_related('assemble', 'group').order_by('-modified_date')
    serializer_class = POFormulaSerializer
    permission_classes = [permissions.IsAuthenticated & EstimatePermissions]
    filter_backends = (filters.DjangoFilterBackend, rf_filters.SearchFilter)
    filterset_class = FormulaFilter
    search_fields = ('name', )


class POFormulaReMarkOnGroupList(POFormulaList):
    queryset = POFormula.objects.filter(is_show=True).\
        prefetch_related(*FORMULA_PREFETCH_RELATED).select_related('assemble', 'group').order_by('-modified_date')
    search_fields = ('name', 'formula', 'quantity', 'markup', 'charge', 'material', 'cost',
                     'unit', 'gross_profit', 'description_of_formula')


class POFormulaCompactList(POFormulaList):
    serializer_class = POFormulaCompactSerializer


class POFormulaDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = POFormula.objects.all().prefetch_related(*FORMULA_PREFETCH_RELATED)
    serializer_class = POFormulaSerializer
    permission_classes = [permissions.IsAuthenticated & EstimatePermissions]


class POFormulaGroupingList(CompanyFilterMixin, generics.ListCreateAPIView):
    queryset = POFormulaGrouping.objects.all().select_related().order_by('-modified_date').distinct()
    serializer_class = POFormulaGroupingSerializer
    permission_classes = [permissions.IsAuthenticated & EstimatePermissions]
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = GroupFormulaFilter


class POFormulaGroupCompactList(POFormulaGroupingList):
    serializer_class = POFormulaGroupCompactSerializer


class POFormulaGroupingCreate(CompanyFilterMixin, generics.CreateAPIView):
    queryset = POFormulaGrouping.objects.all().order_by('-modified_date').distinct()
    serializer_class = GroupFormulasSerializer
    permission_classes = [permissions.IsAuthenticated & EstimatePermissions]


class POFormulaGroupingDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = POFormulaGrouping.objects.all().prefetch_related(*GROUP_PREFETCH_RELATED)
    serializer_class = POFormulaGroupingSerializer
    permission_classes = [permissions.IsAuthenticated & EstimatePermissions]


class DataEntryList(CompanyFilterMixin, generics.ListCreateAPIView):
    queryset = DataEntry.objects.filter(is_show=True).prefetch_related('material_selections', 'unit').select_related('unit').order_by('-modified_date')
    serializer_class = DataEntrySerializer
    permission_classes = [permissions.IsAuthenticated & EstimatePermissions]
    filter_backends = (filters.DjangoFilterBackend, rf_filters.SearchFilter)
    filterset_class = DataEntryFilter
    search_fields = ('name', )


class DataEntryDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = DataEntry.objects.all().prefetch_related('material_selections', 'unit').select_related('unit')
    serializer_class = DataEntrySerializer
    permission_classes = [permissions.IsAuthenticated & EstimatePermissions]

    def destroy(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        if POFormulaToDataEntry.objects.filter(data_entry__pk=pk).exists():
            raise serializers.ValidationError({'error': 'This data entry have been used in other formulas'})
        return super().destroy(request, *args, **kwargs)


class UnitLibraryList(CompanyFilterMixin, generics.ListCreateAPIView):
    queryset = UnitLibrary.objects.all().order_by('-modified_date')
    serializer_class = UnitLibrarySerializer
    permission_classes = [permissions.IsAuthenticated & EstimatePermissions]
    filter_backends = (filters.DjangoFilterBackend, rf_filters.SearchFilter)
    filterset_class = UnitFilter
    search_fields = ('name', )


class UnitLibraryDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = UnitLibrary.objects.all()
    serializer_class = UnitLibrarySerializer
    permission_classes = [permissions.IsAuthenticated & EstimatePermissions]


class DescriptionLibraryList(CompanyFilterMixin, generics.ListCreateAPIView):
    queryset = DescriptionLibrary.objects.all().order_by('-modified_date')
    serializer_class = DescriptionLibrarySerializer
    permission_classes = [permissions.IsAuthenticated & EstimatePermissions]
    filter_backends = (filters.DjangoFilterBackend, rf_filters.SearchFilter)
    filterset_class = DescriptionFilter
    search_fields = ('name', )


class DescriptionLibraryDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = DescriptionLibrary.objects.all()
    serializer_class = DescriptionLibrarySerializer
    permission_classes = [permissions.IsAuthenticated & EstimatePermissions]


class AssembleList(CompanyFilterMixin, generics.ListCreateAPIView):
    queryset = Assemble.objects.filter(
        estimate_templates=None, is_show=True
    ).order_by('-modified_date').prefetch_related(*ASSEMBLE_PREFETCH_RELATED)
    serializer_class = AssembleSerializer
    permission_classes = [permissions.IsAuthenticated & EstimatePermissions]
    filter_backends = (filters.DjangoFilterBackend, rf_filters.SearchFilter)
    filterset_class = AssembleFilter
    search_fields = ('name', 'description')


class AssembleCompactList(AssembleList):
    serializer_class = AssembleCompactSerializer


class AssembleDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Assemble.objects.all().prefetch_related(*ASSEMBLE_PREFETCH_RELATED)
    serializer_class = AssembleSerializer
    permission_classes = [permissions.IsAuthenticated & EstimatePermissions]


class EstimateTemplateList(CompanyFilterMixin, generics.ListCreateAPIView):
    queryset = EstimateTemplate.objects.filter(
        is_show=True).order_by('-modified_date').prefetch_related(*ALL_ESTIMATE_PREFETCH_RELATED)
    serializer_class = EstimateTemplateSerializer
    permission_classes = [permissions.IsAuthenticated & EstimatePermissions]
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = EstimateTemplateFilter


class EstimateTemplateCompactList(EstimateTemplateList):
    serializer_class = EstimateTemplateCompactSerializer


class EstimateTemplateDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = EstimateTemplate.objects.all().prefetch_related(*ALL_ESTIMATE_PREFETCH_RELATED)
    serializer_class = EstimateTemplateSerializer
    permission_classes = [permissions.IsAuthenticated & EstimatePermissions]


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated & EstimatePermissions])
def filter_group_fo_to_fo(request):
    q = Q()
    temp = request.query_params.dict()

    if temp == {}:
        grouping_queryset = POFormulaGrouping.objects.filter(
            company=request.user.company,
        ).order_by('-modified_date').distinct().values()
        for data in grouping_queryset:
            po = POFormula.objects.filter(Q(group_id=data['id']) & q)
            data['group_formulas'] = po
        paginator = LimitOffsetPagination()
        grouping_po_rs = paginator.paginate_queryset(grouping_queryset, request)
        serializer = POFormulaGroupingSerializer(grouping_po_rs, many=True)
        return paginator.get_paginated_response(serializer.data)
    data_filter = {
        "today": {
                "%s__year" % 'modified_date': now().year,
                "%s__month" % 'modified_date': now().month,
                "%s__day" % 'modified_date': now().day,
        },
        "yesterday": {
                "%s__gte" % 'modified_date': now() - timedelta(days=1),
                "%s__lt" % 'modified_date': now(),
        },
        "past-7-days": {
                "%s__gte" % 'modified_date': _truncate(now() - timedelta(days=7)),
                "%s__lt" % 'modified_date': _truncate(now() + timedelta(days=1)),
        },
        "past-14-days": {
                "%s__gte" % 'modified_date': _truncate(now() - timedelta(days=14)),
                "%s__lt" % 'modified_date': _truncate(now() + timedelta(days=1)),
        },
        "past-30-days": {
                "%s__gte" % 'modified_date': _truncate(now() - timedelta(days=30)),
                "%s__lt" % 'modified_date': _truncate(now() + timedelta(days=1)),
        },
        "past-45-days": {
                "%s__gte" % 'modified_date': _truncate(now() - timedelta(days=45)),
                "%s__lt" % 'modified_date': _truncate(now() + timedelta(days=1)),
        },
        "past-90-days": {
                "%s__gte" % 'modified_date': _truncate(now() - timedelta(days=90)),
                "%s__lt" % 'modified_date': _truncate(now() + timedelta(days=1)),
        },
    }
    q &= Q(**{f'company': request.user.company})
    for data in temp:
        if data == 'modified_date' and temp['modified_date'] != str():
            date = datetime.strptime(temp[data], '%Y-%m-%d %H:%M:%S')
            q &= Q(**{f'{data}__gt': date})
        if data == 'created_date' and temp['created_date'] != str():
            date = datetime.strptime(temp[data], '%Y-%m-%d %H:%M:%S')
            q &= Q(**{f'{data}__gt': date})
        if data == 'age_of_formula' and temp['age_of_formula'] != str():
            q &= Q(**data_filter[temp['age_of_formula']])
        if data != 'cost' and data != 'limit' and data != 'offset' and data != 'modified_date' and data != 'created_date' and data != 'age_of_formula':
            q &= Q(**{f'{data}__icontains': temp[data]})
        if data == 'cost' and temp[data] != str():
            q &= Q(cost__gt=temp[data])

    formula_queryset = POFormula.objects.filter(q)
    grouping_queryset = POFormulaGrouping.objects.filter(
        company=request.user.company,
        group_formulas__in=Subquery(formula_queryset.values('pk'))
    ).order_by('-modified_date').distinct().values()

    for data in grouping_queryset:
        po = POFormula.objects.filter(Q(group_id=data['id']) & q)
        data['group_formulas'] = po
    paginator = LimitOffsetPagination()
    grouping_po_rs = paginator.paginate_queryset(grouping_queryset, request)
    serializer = POFormulaGroupingSerializer(grouping_po_rs, many=True)
    return paginator.get_paginated_response(serializer.data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated & EstimatePermissions])
def get_linked_descriptions(request):
    """
    Get linked description from estimate and catalog
    """
    search_query = {'linked_description__icontains': request.GET.get('search', '')}
    dl = DescriptionLibrary.objects.filter(**search_query, company=get_request().user.company)
    paginator = LimitOffsetPagination()
    estimate_result = paginator.paginate_queryset(dl, request)
    estimate_serializer = LinkedDescriptionSerializer(estimate_result, many=True)
    return paginator.get_paginated_response(estimate_serializer.data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated & EstimatePermissions])
def get_linked_description(request, pk):
    """
    Get linked description from estimate and catalog
    """
    if 'estimate' in pk:
        obj = get_object_or_404(DescriptionLibrary.objects.filter(company=request.user.company), pk=pk.split(':')[1])
    else:
        obj = get_object_or_404(DataPoint.objects.filter(company=request.user.company), pk=pk.split(':')[1])
    serializer = LinkedDescriptionSerializer(obj)
    return Response(status=status.HTTP_200_OK, data=serializer.data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated & EstimatePermissions])
def get_formula_tag_value(request, pk):
    """
    Get linked description from estimate and catalog
    """
    estimate = get_object_or_404(EstimateTemplate.objects.filter(company=request.user.company), pk=pk)
    formulas = estimate.get_formula()
    data = []
    for formula in formulas:
        data.extend(formula.parse_value_with_tag())
    return Response(status=status.HTTP_200_OK, data=data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated & EstimatePermissions])
def get_tag_formula(request):
    formulas = POFormula.objects.filter(company=get_request().user.company, is_show=True)
    serializer = TaggingSerializer(formulas, many=True)
    return Response(data=serializer.data, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated & EstimatePermissions])
def get_tag_data_point(request):
    # data_points = DataPoint.objects.filter(company=get_request().user.company)
    # serializer = TaggingSerializer(data_points, many=True)
    return Response(data=[], status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated & EstimatePermissions])
def get_tag_levels(request):
    material_id = request.GET.get('material_id')
    if not material_id:
        return Response(data='Missing material_id parameter!', status=status.HTTP_400_BAD_REQUEST)
    catalog_pk = material_id.split(':')[0]
    catalog = get_object_or_404(Catalog.objects.filter(company=request.user.company), pk=catalog_pk)
    ancestor = catalog.get_ancestors()

    serializer = CatalogLevelValueSerializer(ancestor[::-1], many=True)
    return Response(data=serializer.data, status=status.HTTP_200_OK)


@api_view(['PUT'])
@permission_classes([permissions.IsAuthenticated & EstimatePermissions])
def unlink_group(request):
    ids = request.data
    formulas = POFormula.objects.filter(id__in=ids)
    formulas.update(group=None)
    serializer = POFormulaSerializer(formulas, many=True)
    return Response(data=serializer.data, status=status.HTTP_200_OK)


@api_view(['PUT'])
@permission_classes([permissions.IsAuthenticated & EstimatePermissions])
def add_existing_formula(request, pk):
    ids = request.data
    formulas = POFormula.objects.filter(id__in=ids)
    formulas.update(group=pk)
    serializer = POFormulaSerializer(formulas, many=True)
    return Response(data=serializer.data, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated & EstimatePermissions])
def get_material_by_data_entry(request, pk):
    de = DataEntry.objects.get(pk=pk)
    categories = de.material_selections.all()
    children = Catalog.objects.none()
    for category in categories:
        children |= Catalog.objects.filter(pk__in=category.get_all_descendant(have_self=True))
    children = children.difference(Catalog.objects.filter(c_table=Value('{}')))
    data = parse_c_table(children)
    return Response(status=status.HTTP_200_OK, data=data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated & EstimatePermissions])
def get_material_from_formula(request, pk):
    mv = get_object_or_404(MaterialView.objects.filter(company=request.user.company), pk=pk)
    catagory_id = mv.catalog_materials[-1].get('id')
    cat = get_object_or_404(Catalog.objects.all(), pk=catagory_id)
    sub_categories = Catalog.objects.filter(pk__in=cat.get_all_descendant(have_self=True))
    data = parse_c_table(sub_categories)
    return Response(status=status.HTTP_200_OK, data=data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated & EstimatePermissions])
def get_option_data_entry(request, pk):
    de = DataEntry.objects.get(pk=pk)
    categories = de.material_selections.all()
    children = Catalog.objects.none()
    for category in categories:
        children |= Catalog.objects.filter(parents=category)
    serializer = CatalogEstimateWithParentSerializer(children, many=True)
    return Response(status=status.HTTP_200_OK, data=serializer.data)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([permissions.IsAuthenticated & EstimatePermissions])
def action_related_formulas(request, pk):
    formula = get_object_or_404(POFormula.objects.all(), pk=pk)
    if request.method == 'GET':
        data = formula.get_related_formula()
        return Response(status=status.HTTP_200_OK, data=data)

    if request.method == 'PUT':
        serializer = POFormulaSerializer(formula, request.data, context={'request': request})
        serializer.is_valid()
        obj = serializer.save()

        # Update related formulas
        related_formulas_ids = request.data.pop('related_formulas', [])
        data = request.data
        delist_column = ['group', 'assemble', 'is_show', 'id']
        for column in delist_column:
            data.pop(column)
        related_formulas = POFormula.objects.filter(pk__in=related_formulas_ids)
        for formula in related_formulas:
            serializer = POFormulaSerializer(formula, data, context={'request': request})
            serializer.is_valid()
            obj = serializer.save()
        return Response(status=status.HTTP_200_OK)

    if request.method == 'DELETE':
        assembles_ids = request.data.pop('assembles', [])
        assembles = Assemble.objects.filter(id__in=assembles_ids)
        POFormula.objects.filter(original=pk, assemble__in=assembles, is_show=False).delete()
        POFormula.objects.filter(id=pk).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated & EstimatePermissions])
def export_data_unit_library(request):
    workbook = Workbook()
    unit_library_sheet = workbook.create_sheet(title='UnitLibrary')
    unit_library = UnitLibrary.objects.filter(company=request.user.company)
    unit_library_fields = ['Name', 'Description', 'User Create', 'User Update', 'Create Date', 'Update Date']
    unit_library_sheet.append(unit_library_fields)
    for index, data_unit_library in enumerate(unit_library, 1):
        user_create = data_unit_library.user_create.username
        user_update = data_unit_library.user_update
        create_date = data_unit_library.created_date
        if user_update is not None:
            user_update = user_update.username
        else:
            user_update = ''

        if create_date is not None:
            create_date = create_date.replace(tzinfo=None)
        else:
            create_date = ''

        modified_date = data_unit_library.modified_date
        if modified_date is not None:
            modified_date = modified_date.replace(tzinfo=None)
        else:
            modified_date = ''
        row_data = [
            data_unit_library.name, data_unit_library.description, user_create, user_update, create_date, modified_date
        ]

        unit_library_sheet.append(row_data)

    return file_response(workbook=workbook, title='Unit_Library')


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated & EstimatePermissions])
def import_data_unit_library(request):
    file = request.FILES['file']
    workbook = load_workbook(file)
    unit_library_sheet = workbook['UnitLibrary']

    max_row = unit_library_sheet.max_row
    temp_rs = []
    for row_number in range(max_row, 1, -1):
        row = unit_library_sheet[row_number]
        data_create = {
            'name': row[0].value,
            'description': row[1].value
        }
        ul = UnitLibrary.objects.create(**data_create)
        temp_rs.append(ul)

    rs = UnitLibrarySerializer(
        temp_rs, many=True, context={'request': request}).data
    return Response(status=status.HTTP_200_OK, data=rs)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated & EstimatePermissions])
def export_data_description_library(request):
    workbook = Workbook()
    description_library_sheet = workbook.create_sheet(title='LinkDescriptionLibrary')
    description_library = DescriptionLibrary.objects.filter(company=request.user.company)
    description_library_fields = ['Name', 'Link Description', 'User Create', 'User Update', 'Create Date', 'Update Date']
    description_library_sheet.append(description_library_fields)
    for index, data_description_library in enumerate(description_library, 1):
        user_create = data_description_library.user_create.username
        user_update = data_description_library.user_update
        create_date = data_description_library.created_date
        if user_update is not None:
            user_update = user_update.username
        else:
            user_update = ''

        if create_date is not None:
            create_date = create_date.replace(tzinfo=None)
        else:
            create_date = ''

        modified_date = data_description_library.modified_date
        if modified_date is not None:
            modified_date = modified_date.replace(tzinfo=None)
        else:
            modified_date = ''
        row_data = [
            data_description_library.name, data_description_library.linked_description, user_create, user_update, create_date, modified_date
        ]

        description_library_sheet.append(row_data)

    return file_response(workbook=workbook, title='Description_Library')


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated & EstimatePermissions])
def import_data_description_library(request):
    file = request.FILES['file']
    workbook = load_workbook(file)
    description_library_sheet = workbook['LinkDescriptionLibrary']

    max_row = description_library_sheet.max_row
    temp_rs = []
    for row_number in range(max_row, 1, -1):
        row = description_library_sheet[row_number]
        data_create = {
            'name': row[0].value,
            'linked_description': row[1].value
        }
        ul = DescriptionLibrary.objects.create(**data_create)
        temp_rs.append(ul)

    rs = DescriptionLibrarySerializer(
        temp_rs, many=True, context={'request': request}).data
    return Response(status=status.HTTP_200_OK, data=rs)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated & EstimatePermissions])
def export_data_entry(request):
    workbook = Workbook()
    data_entry_sheet = workbook.create_sheet(title='Data_Entry')
    data_entries = DataEntry.objects.filter(company=request.user.company)
    data_entry_fields = ['Name', 'Unit', 'Is Dropdown', 'Dropdown', 'Is Material Selection', 'Material Selection']
    data_entry_sheet.append(data_entry_fields)
    for data_entry in data_entries:
        data_entry_sheet.append(data_entry.export_to_json())
    return file_response(workbook=workbook, title='Data Entry')


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated & EstimatePermissions])
def import_data_entry(request):
    file = request.FILES['file']
    workbook = load_workbook(file)
    data_entry_sheet = workbook['Data_Entry']

    max_row = data_entry_sheet.max_row
    temp_rs = []
    for row_number in range(max_row, 1, -1):
        row = data_entry_sheet[row_number]
        unit = None
        if row[1]:
            unit = UnitLibrary.objects.get_or_create(name=row[1].value, company=request.user.company)[0]
        data_create = {
            'name': row[0].value,
            'unit': unit,
            'is_dropdown': row[2].value,
            'dropdown': eval(row[3].value),
            'is_material_selection': row[4].value,
        }

        ul = DataEntry.objects.create(**data_create)
        if row[5].value:
            ul.material_selections.add(*Catalog.objects.filter(id__in=row[5].value))
        temp_rs.append(ul)

    rs = DataEntrySerializer(
        temp_rs, many=True, context={'request': request}).data
    return Response(status=status.HTTP_200_OK, data=rs)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated & EstimatePermissions])
def export_formula(request):
    workbook = Workbook()
    formula_sheet = workbook.create_sheet(title='Formula')
    formulas = POFormula.objects.filter(company=request.user.company, is_show=True)
    formula_fields = ['Name', 'Linked Description', 'Formula', 'Group', 'Quantity', 'Markup', 'Charge',
                      'Material', 'Unit', 'Unit Price', 'Cost', 'Total Cost', 'Formula Mention', 'Gross Profit',
                      'Description', 'Scenario', 'Material Data Entry', 'Catalog Material']
    formula_sheet.append(formula_fields)
    for formula in formulas:
        formula_sheet.append(formula.export_to_json())
    return file_response(workbook=workbook, title='Formula')


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated & EstimatePermissions])
def import_formula(request):
    file = request.FILES['file']
    workbook = load_workbook(file)
    formula_sheet = workbook['Formula']

    max_row = formula_sheet.max_row
    temp_rs = []
    for row_number in range(max_row, 1, -1):
        row = formula_sheet[row_number]
        data_create = {
            'name': row[0].value,
            'linked_description': row[1].value or '',
            'formula': row[2].value or '',
            'quantity': row[4].value or '',
            'markup': row[5].value or '',
            'charge': row[6].value or '0',
            'material': row[7].value or {},
            'unit': row[8].value or '',
            'unit_price': row[9].value or '0',
            'cost': row[10].value or '0',
            'total_cost': row[11].value or '0',
            'formula_mentions': row[12].value or '',
            'gross_profit': row[13].value or '',
            'description_of_formula': row[14].value or '',
            'formula_scenario': row[15].value or '',
            'material_data_entry': eval(row[16].value),
            'catalog_materials': eval(row[17].value),
        }

        ul = POFormula.objects.create(**data_create)
        temp_rs.append(ul)

    rs = POFormulaGroupCompactSerializer(
        temp_rs, many=True, context={'request': request}).data
    return Response(status=status.HTTP_200_OK, data=rs)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated & EstimatePermissions])
def export_assemble(request):
    workbook = Workbook()
    assemble_sheet = workbook.create_sheet(title='Assemble')
    assembles = Assemble.objects.filter(company=request.user.company, is_show=True)
    assemble_fields = ['Name', 'Meta']
    assemble_sheet.append(assemble_fields)
    for assemble in assembles:
        assemble_sheet.append([*assemble.export_to_json(), str(json.dumps(AssembleSerializer(assemble).data))])
    return file_response(workbook=workbook, title='Assemble')


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated & EstimatePermissions])
def export_estimate(request):
    workbook = Workbook()
    estimate_sheet = workbook.create_sheet(title='Estimate')
    estimates = EstimateTemplate.objects.filter(company=request.user.company, is_show=True)
    estimate_fields = ['Name', 'Meta']
    estimate_sheet.append(estimate_fields)
    for estimate in estimates:
        estimate_sheet.append([*estimate.export_to_json(), str(json.dumps(EstimateTemplateSerializer(estimate).data))])
    return file_response(workbook=workbook, title='Estimate')


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated & EstimatePermissions])
def import_assemble(request):
    file = request.FILES['file']
    workbook = load_workbook(file)
    assemble_sheet = workbook['Assemble']

    max_row = assemble_sheet.max_row
    temp_rs = []
    for row_number in range(max_row, 1, -1):
        row = assemble_sheet[row_number]
        data_create = {
            'name': row[0].value,
            **eval(row[1].value)
        }

        serializer = AssembleSerializer(data=data_create, context={'request': request})
        if serializer.is_valid(raise_exception=False):
            temp_rs.append(serializer.save())

    rs = AssembleSerializer(
        temp_rs, many=True, context={'request': request}).data
    return Response(status=status.HTTP_200_OK, data=rs)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated & EstimatePermissions])
def import_estimate(request):
    file = request.FILES['file']
    workbook = load_workbook(file)
    estimate_sheet = workbook['Estimate']

    max_row = estimate_sheet.max_row
    temp_rs = []
    for row_number in range(max_row, 1, -1):
        row = estimate_sheet[row_number]
        data_create = {
            'name': row[0].value,
            **eval(row[1].value)
        }
        serializer = EstimateTemplateSerializer(data=data_create, context={'request': request})
        if serializer.is_valid(raise_exception=False):
            temp_rs.append(serializer.save())

    rs = EstimateTemplateSerializer(
        temp_rs, many=True, context={'request': request}).data
    return Response(status=status.HTTP_200_OK, data=rs)


@api_view(['GET', 'PUT'])
@permission_classes([permissions.IsAuthenticated & EstimatePermissions])
def check_update_data_entry(request, pk):
    """
    Payload: {"data_entry": Data Entry object, "formulas": [id]}

    Updating Data Entry for formulas
    """
    data_entry = get_object_or_404(DataEntry.objects.all(), pk=pk)
    self_data_entries = data_entry.poformulatodataentry_set.all()

    if request.method == 'PUT':
        formula_ids = request.data.get('formulas', [])
        data_entry_params = request.data.get('data_entry', {})
        all_relation_number = POFormula.objects.filter(self_data_entries__in=self_data_entries, is_show=True).distinct().count()
        updating_formula_number = len(formula_ids)
        old_obj = get_object_or_404(DataEntry.objects.all(), pk=pk)
        if updating_formula_number != all_relation_number:
            # Create new object
            old_serializer = DataEntrySerializer(old_obj).data
            old_serializer.pop('id', None)
            new_serializer = DataEntrySerializer(data=old_serializer)
            new_serializer.is_valid(raise_exception=True)
            new_obj = new_serializer.save(is_show=True)

            # change formula relation between old and new
            formulas = POFormula.objects.filter(pk__in=formula_ids)
            formula_with_data_entry = POFormulaToDataEntry.objects.filter(data_entry=old_obj).exclude(po_formula__in=formulas)
            formula_with_data_entry.update(data_entry=new_obj)

        # Update data entry
        data_entry_params.pop('id', None)
        serializer = DataEntrySerializer(instance=old_obj, data=data_entry_params, context={'request': request})
        serializer.is_valid(raise_exception=True)
        obj = serializer.save()

    data = {}
    data['has_relation'] = data_entry.poformulatodataentry_set.all().exists()
    formulas = POFormula.objects.filter(self_data_entries__in=self_data_entries, is_show=True).distinct()
    data['formula_relation'] = formulas.values('id', 'name')
    data['data_entry'] = DataEntrySerializer(data_entry).data
    return Response(status=status.HTTP_200_OK, data=data)


@api_view(['GET', 'PUT'])
@permission_classes([permissions.IsAuthenticated & EstimatePermissions])
def check_update_estimate(request, pk):
    ProposalWriting = apps.get_model('sales', 'ProposalWriting')
    PriceComparison = apps.get_model('sales', 'PriceComparison')
    estimate = get_object_or_404(EstimateTemplate.objects.all(), pk=pk)
    proposal_writings = ProposalWriting.objects.filter(writing_groups__estimate_templates__original=pk)
    price_comparisons = PriceComparison.objects.filter(groups__estimate_templates__original=pk)

    data = {}
    data['has_relation'] = proposal_writings.exists() or price_comparisons.exists()
    data['proposal_writings'] = proposal_writings.values('id', 'name')
    data['price_comparisons'] = price_comparisons.values('id', 'name')

    return Response(status=status.HTTP_200_OK, data=data)
