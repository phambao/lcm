import uuid

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

from api.serializers.base import ActivityLogSerializer
from ..filters import SearchFilter, ColumnFilter, ConfigFilter, GridSettingFilter, ActivityLogFilter
from ..models.config import Column, Search, Config, GridSetting, FileBuilder365
from ..serializers.base import ContentTypeSerializer, FileBuilder365ReqSerializer, \
    FileBuilder365ResSerializer
from ..serializers.config import SearchSerializer, ColumnSerializer, ConfigSerializer, GridSettingSerializer, \
    CompanySerializer, DivisionSerializer
from api.models import ActivityLog, CompanyBuilder, DivisionCompany


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


class CompanyListView(generics.ListCreateAPIView):
    queryset = CompanyBuilder.objects.all()
    serializer_class = CompanySerializer
    permission_classes = [permissions.IsAuthenticated]


class CompanyDetailGenericView(generics.RetrieveUpdateDestroyAPIView):
    queryset = CompanyBuilder.objects.all()
    serializer_class = CompanySerializer
    permission_classes = [permissions.IsAuthenticated]


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


class ActivityLogList(generics.ListCreateAPIView, CompanyFilterMixin):
    queryset = ActivityLog.objects.all().order_by('-created_date').prefetch_related(
        'user_create', 'user_create__groups', 'user_create__user_permissions'
    )
    serializer_class = ActivityLogSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = ActivityLogFilter


class ActivityLogDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = ActivityLog.objects.all()
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


@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
def delete_models(request, content_type):
    ids = request.data
    model = ContentType.objects.get_for_id(content_type)
    deleted_data = model.model_class().objects.filter(pk__in=ids).delete()
    return Response(status=status.HTTP_204_NO_CONTENT, data=deleted_data)


@api_view(['PUT'])
@permission_classes([permissions.IsAuthenticated])
def update_language_user(request, *args, **kwargs):
    lang = kwargs.get('lang')
    user = request.user
    user.lang = lang
    user.save()
    return Response(status=status.HTTP_200_OK)
