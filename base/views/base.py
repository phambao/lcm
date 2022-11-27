from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.contrib.contenttypes.models import ContentType
from rest_framework import generics, permissions, status
from django_filters import rest_framework as filters

from ..filters import SearchFilter, ColumnFilter, ConfigFilter
from ..models.config import Column, Search, Config
from ..serializers.base import ContentTypeSerializer
from ..serializers.config import SearchSerializer, ColumnSerializer, ConfigSerializer


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
