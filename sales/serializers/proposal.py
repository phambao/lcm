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
    proposal_widget_element = ProposalWidgetSerializer('proposal_element', allow_null=True, required=False, many=True)

    class Meta:
        model = ProposalElement
        fields = ('id', 'proposal_template', 'display_order', 'proposal_widget_element', 'title')


class ProposalTemplateSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)
    proposal_template_element = ProposalElementSerializer('proposal_template', allow_null=True, required=False, many=True)

    class Meta:
        model = ProposalTemplate
        fields = ('id', 'name', 'proposal_template_element')

    def create(self, validated_data):
        elements = pop(validated_data, 'proposal_template_element', [])
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

    def update(self, instance, data):
        elements = pop(data, 'proposal_template_element', [])
        proposal_template = ProposalTemplate.objects.filter(pk=instance.pk)
        proposal_template.update(**data)
        data_create_widget = []
        proposal_element = ProposalElement.objects.filter(proposal_template=proposal_template.first().id)
        proposal_element.delete()
        for element in elements:
            proposal_element = ProposalElement.objects.create(
                proposal_template=proposal_template.first(),
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
        instance.refresh_from_db()
        return instance
