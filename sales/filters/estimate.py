from django_filters import rest_framework as filters

from sales.models.estimate import TemplateName


class TemplateNameFilter(filters.FilterSet):
    parent = filters.ModelChoiceFilter(queryset=TemplateName.objects.all())
    is_null_parent = filters.BooleanFilter(field_name='parent', lookup_expr='isnull')

    class Meta:
        model = TemplateName
        fields = ('menu', )
