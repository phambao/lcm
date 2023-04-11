from rest_framework import serializers

from base.utils import pop
from sales.models import ProposalTemplate, ProposalElement, ProposalWidget


class ProposalWidgetSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)

    class Meta:
        model = ProposalWidget
        fields = ('id', 'proposal_element', 'type_widget', 'title', 'display_order', 'data_widget')


class ProposalElementSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)
    widget = ProposalWidgetSerializer(allow_null=True, required=False, many=True)

    class Meta:
        model = ProposalElement
        fields = ('id', 'proposal_template', 'display_order', 'widget', 'title')

    def to_representation(self, instance):
        data = super().to_representation(instance)
        widget = instance.proposal_widget_element.all()
        rs = ProposalWidgetSerializer(widget, many=True)
        data['widget'] = rs.data
        return data


class ProposalTemplateSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)
    element = ProposalElementSerializer(allow_null=True, required=False, many=True)

    class Meta:
        model = ProposalTemplate
        fields = ('id', 'name', 'element')

    def create(self, validated_data):
        request = self.context['request']
        user_create = user_update = request.user
        elements = pop(validated_data, 'element', [])
        proposal_template = ProposalTemplate.objects.create(
            **validated_data
        )
        data_create_widget = []
        for element in elements:
            proposal_element = ProposalElement.objects.create(
                proposal_template=proposal_template,
                title=element['title'],
                display_order=element['display_order']
            )
            for widget in element['widget']:
                data = ProposalWidget(
                    proposal_element=proposal_element,
                    type_widget=widget['type_widget'],
                    title=widget['title'],
                    display_order=widget['display_order'],
                    data_widget=widget['data_widget']
                )
                data_create_widget.append(data)

        ProposalWidget.objects.bulk_create(data_create_widget)
        return proposal_template

    def to_representation(self, instance):
        data = super().to_representation(instance)
        element = instance.proposal_template_element.all()
        rs = ProposalElementSerializer(element, many=True)
        data['element'] = rs.data
        return data
