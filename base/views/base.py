import uuid

from django.utils import timezone
from django.utils.translation import gettext  as _
from django.core.files.base import ContentFile
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth import get_user_model
from rest_framework import generics, permissions, status
from django_filters import rest_framework as filters
from rest_framework.viewsets import GenericViewSet

from api.middleware import get_request
from api.serializers.base import ActivityLogSerializer
from ..filters import SearchFilter, ColumnFilter, ConfigFilter, GridSettingFilter, ActivityLogFilter
from ..models.config import Column, Search, Config, GridSetting, FileBuilder365, Question, Answer, CompanyAnswerQuestion
from ..serializers.base import ContentTypeSerializer, FileBuilder365ReqSerializer, \
    FileBuilder365ResSerializer, DeleteDataSerializer
from ..serializers.config import SearchSerializer, ColumnSerializer, ConfigSerializer, GridSettingSerializer, \
    CompanySerializer, DivisionSerializer, QuestionSerializer, AnswerSerializer, CompanyAnswerQuestionSerializer, \
    CompanyAnswerQuestionResSerializer
from api.models import ActivityLog, CompanyBuilder, DivisionCompany, Action


class ContentTypeList(generics.ListAPIView):
    """
    Return all the table's name in db
    """
    queryset = ContentType.objects.all()
    serializer_class = ContentTypeSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None


class SearchLeadGenericView(generics.ListCreateAPIView):
    queryset = Search.objects.all()
    serializer_class = SearchSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = SearchFilter

    def get_queryset(self):
        data = super().get_queryset()
        data = data.filter(user=self.request.user)
        return data

    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        data['user'] = request.user.id
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class SearchLeadDetailGenericView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Search.objects.all()
    serializer_class = SearchSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        data = super().get_queryset()
        data = data.filter(user=self.request.user)
        return data


class ColumnLeadGenericView(generics.ListCreateAPIView):
    queryset = Column.objects.all()
    serializer_class = ColumnSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = ColumnFilter

    def get_queryset(self):
        data = super().get_queryset()
        data = data.filter(user=self.request.user)
        return data

    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        data['user'] = request.user.id
        try:
            data['content_type'] = ContentType.objects.get(model=data['model']).id
        except ContentType.DoesNotExist:
            raise ValidationError({'model': 'Model not found'})
        del data['model']
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class ColumnLeadDetailGenericView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Column.objects.all()
    serializer_class = ColumnSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        data = super().get_queryset()
        data = data.filter(user=self.request.user)
        return data


class GridSettingDetailGenericView(generics.RetrieveUpdateDestroyAPIView):
    queryset = GridSetting.objects.all()
    serializer_class = GridSettingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        data = super().get_queryset()
        data = data.filter(user=self.request.user)
        return data


class GridSettingListView(generics.ListCreateAPIView):
    queryset = GridSetting.objects.all()
    serializer_class = GridSettingSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = GridSettingFilter

    def get_queryset(self):
        data = super().get_queryset()
        data = data.filter(user=self.request.user)
        return data

    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        data['user'] = request.user.id
        try:
            data['content_type'] = ContentType.objects.get(model=data['model']).id
        except ContentType.DoesNotExist:
            raise ValidationError({'model': 'Model not found'})
        del data['model']
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class CompanyListView(generics.CreateAPIView):
    queryset = CompanyBuilder.objects.all()
    serializer_class = CompanySerializer
    # permission_classes = [permissions.IsAuthenticated]


class CompanyDetailGenericView(generics.RetrieveUpdateDestroyAPIView):
    queryset = CompanyBuilder.objects.all()
    serializer_class = CompanySerializer
    # permission_classes = [permissions.IsAuthenticated]


class DivisionListView(generics.ListCreateAPIView):
    queryset = DivisionCompany.objects.all()
    serializer_class = DivisionSerializer
    permission_classes = [permissions.IsAuthenticated]


class DivisionDetailGenericView(generics.RetrieveUpdateDestroyAPIView):
    queryset = DivisionCompany.objects.all()
    serializer_class = DivisionSerializer
    permission_classes = [permissions.IsAuthenticated]


class CompanyFilterMixin:
    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.filter(company=self.request.user.company)
        return queryset


class QuestionGenericView(generics.ListCreateAPIView):
    queryset = Question.objects.all()
    serializer_class = QuestionSerializer


class QuestionDetailGenericView(generics.RetrieveAPIView):
    queryset = Question.objects.all()
    serializer_class = QuestionSerializer


class AnswerGenericView(generics.ListCreateAPIView):
    queryset = Answer.objects.all()
    serializer_class = AnswerSerializer


class AnswerDetailGenericView(generics.RetrieveAPIView):
    queryset = Answer.objects.all()
    serializer_class = AnswerSerializer


class CompanyAnswerQuestionSerializerGenericView(generics.ListAPIView):
    queryset = CompanyAnswerQuestion.objects.all()
    serializer_class = CompanyAnswerQuestionResSerializer


class CompanyAnswerQuestionSerializerDetailGenericView(generics.RetrieveAPIView):
    queryset = CompanyAnswerQuestion.objects.all()
    serializer_class = CompanyAnswerQuestionResSerializer


@api_view(['POST'])
def create_question_answer_company(request):
    serializer = CompanyAnswerQuestionSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data_create = serializer.validated_data
    questions_info = data_create['info']
    company = data_create['company']
    for question_answer in questions_info:
        question_id = question_answer['question']
        company_question = CompanyAnswerQuestion.objects.create(
                    question_id=question_id,
                    company=company
        )
        data_answer = Answer.objects.filter(pk__in=[at['id'] for at in question_answer['answer']])
        company_question.answer.add(*data_answer)
    data_rs = CompanyAnswerQuestion.objects.filter(company=company)
    rs = CompanyAnswerQuestionResSerializer(
        data_rs, many=True, context={'request': request}).data
    return Response(status=status.HTTP_201_CREATED, data=rs)


@api_view(['PUT'])
@permission_classes([permissions.IsAuthenticated])
def update_question_answer_company(request, *args, **kwargs):
    company_id = kwargs.get('company_id')
    get_object_or_404(CompanyBuilder.objects.all(), pk=company_id)
    serializer = CompanyAnswerQuestionSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data_create = serializer.validated_data
    questions_info = data_create['info']
    company = data_create['company']
    temp = CompanyAnswerQuestion.objects.filter(company=company_id)
    temp.delete()
    for question_answer in questions_info:
        question_id = question_answer['question']
        company_question = CompanyAnswerQuestion.objects.create(
                    question_id=question_id,
                    company=company
        )
        data_answer = Answer.objects.filter(pk__in=[at['id'] for at in question_answer['answer']])
        company_question.answer.add(*data_answer)
    data_rs = CompanyAnswerQuestion.objects.filter(company=company)
    rs = CompanyAnswerQuestionResSerializer(
        data_rs, many=True, context={'request': request}).data
    return Response(status=status.HTTP_201_CREATED, data=rs)


@api_view(['GET', 'PUT'])
@permission_classes([permissions.IsAuthenticated])
def config_view(request, model):
    if request.method == 'GET':
        try:
            config = Config.objects.get(user=request.user, content_type__model__exact=model)
        except Config.DoesNotExist:
            content_type = ContentType.objects.get(model=model)
            settings = {}
            if model == 'leaddetail':
                settings = {"search": None,
                            "column": []}
            config = Config.objects.create(user=request.user, content_type=content_type, settings=settings)
        serializer = ConfigSerializer(config)
        return Response(status=status.HTTP_200_OK, data=serializer.data)

    if request.method == 'PUT':
        config = Config.objects.get(user=request.user, content_type__model__exact=model)
        config.settings = request.data['settings']
        config.save()
        config.refresh_from_db()
        serializer = ConfigSerializer(config)
        return Response(status=status.HTTP_200_OK, data=serializer.data)
    return Response(status=status.HTTP_204_NO_CONTENT)


class ActivityLogList(CompanyFilterMixin, generics.ListCreateAPIView):
    queryset = ActivityLog.objects.all().order_by('-created_date').prefetch_related(
        'user_create', 'user_create__groups', 'user_create__user_permissions'
    )
    serializer_class = ActivityLogSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = ActivityLogFilter


class ActivityLogDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = ActivityLog.objects.all().prefetch_related(
        'user_create', 'user_create__groups', 'user_create__user_permissions'
    )
    serializer_class = ActivityLogSerializer
    permission_classes = [permissions.IsAuthenticated]


@api_view(['PUT'])
@permission_classes([permissions.IsAuthenticated])
def active_column(request, pk):
    column = get_object_or_404(Column, pk=pk, user=request.user)
    Column.objects.filter(is_active=True, user=request.user).update(is_active=False)
    column.is_active = True
    column.save()
    serializer = ColumnSerializer(column)
    return Response(status=status.HTTP_200_OK, data=serializer.data)


class FileMessageTodoGenericView(GenericViewSet):
    serializer_class = FileBuilder365ReqSerializer
    permission_classes = [permissions.IsAuthenticated]

    def create_file(self, request, **kwargs):
        serializer = FileBuilder365ReqSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        files = request.FILES.getlist('file')
        attachment_create = list()
        for file in files:
            file_name = uuid.uuid4().hex + '.' + file.name.split('.')[-1]
            content_file = ContentFile(file.read(), name=file_name)
            attachment = FileBuilder365(
                file=content_file,
                user_create=user,
                user_update=user,
                name=file.name
            )
            attachment_create.append(attachment)

        attachments = FileBuilder365.objects.bulk_create(attachment_create)

        data = FileBuilder365ResSerializer(
            attachments, many=True, context={'request': request}).data
        return Response(status=status.HTTP_200_OK, data=data)


def log_delete_action(objs, content_type):
    company = get_request().user.company
    ActivityLog.objects.bulk_create(
        [
            ActivityLog(content_type=content_type, content_object=obj, object_id=obj.pk,
                        action=Action.DELETE, last_state=DeleteDataSerializer(obj).data, next_state={}, company=company)
            for obj in objs
        ]
    )


@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
def delete_models(request, content_type):
    from sales import models
    ids = request.data
    model = ContentType.objects.get_for_id(content_type).model_class()
    deleted_data = model.objects.filter(pk__in=ids)
    can_delete = False
    if model in [models.EstimateTemplate, models.Assemble, models.POFormula, models.DataEntry, models.UnitLibrary, models.DescriptionLibrary]:
        if request.user.has_perm('sales.delete_estimatetemplate'):
            can_delete = True

    elif model in [models.PriceComparison, models.ProposalWriting, models.ProposalTemplate]:
        if request.user.has_perm('sales.delete_proposalwriting'):
            can_delete = True

    elif model in [models.ChangeOrder]:
        if request.user.has_perm('sales.delete_changeorder'):
            can_delete = True

    elif model in [models.Invoice]:
        if request.user.has_perm('sales.delete_invoice'):
            can_delete = True

    elif model in [models.ScheduleEvent, models.ToDo, models.DailyLog]:
        if request.user.has_perm('sales.delete_scheduleevent'):
            can_delete = True

    elif model in [models.Catalog, models.CatalogLevel]:
        if request.user.has_perm('sales.delete_catalog'):
            can_delete = True

    elif model in [models.Catalog, models.LeadDetail]:
        if request.user.has_perm('sales.delete_leaddetail'):
            can_delete = True
    else:
        can_delete = True

    if can_delete:
        log_delete_action(deleted_data, ContentType.objects.get_for_model(model))
        deleted_data.delete()
    return Response(status=status.HTTP_204_NO_CONTENT, data=deleted_data)


@api_view(['PUT'])
@permission_classes([permissions.IsAuthenticated])
def update_language_user(request, *args, **kwargs):
    lang = kwargs.get('lang')
    user = request.user
    user.lang = lang
    user.save()
    return Response(status=status.HTTP_200_OK)
