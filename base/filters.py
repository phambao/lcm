from django.contrib.contenttypes.models import ContentType
from django_filters import rest_framework as filters

from api.models import ActivityLog
from base.models.config import Search, Column, Config, GridSetting


class SearchFilter(filters.FilterSet):
    content_type = filters.ModelChoiceFilter(queryset=ContentType.objects.all())

    class Meta:
        model = Search
        fields = ('content_type',)


class ColumnFilter(filters.FilterSet):
    content_type = filters.ModelChoiceFilter(queryset=ContentType.objects.all())
    model = filters.CharFilter(field_name='content_type__model', lookup_expr='exact')
    is_public = filters.BooleanFilter(field_name='is_public', method='get_public')
    is_active = filters.BooleanFilter(field_name='is_active')

    class Meta:
        model = Column
        fields = ('content_type', 'model')

    def get_public(self, queryset, name, value):
        return Column.objects.filter(is_public=value).exclude(user=self.request.user)


class GridSettingFilter(filters.FilterSet):
    content_type = filters.ModelChoiceFilter(queryset=ContentType.objects.all())
    model = filters.CharFilter(field_name='content_type__model', lookup_expr='exact')
    is_public = filters.BooleanFilter(field_name='is_public', method='get_public')

    class Meta:
        model = GridSetting
        fields = ('content_type', 'model')

    def get_public(self, queryset, name, value):
        return GridSetting.objects.filter(is_public=value)


class ConfigFilter(filters.FilterSet):
    content_type = filters.ModelChoiceFilter(queryset=ContentType.objects.all())

    class Meta:
        model = Config
        fields = ('content_type',)


class ActivityLogFilter(filters.FilterSet):
    created_date = filters.DateTimeFilter(field_name='created_date', lookup_expr='gt')
    is_full_last_state = filters.BooleanFilter(method=lambda query, name, value: query, lookup_expr='gt')

    class Meta:
        model = ActivityLog
        fields = ('content_type', 'object_id', 'user_create', 'created_date')
