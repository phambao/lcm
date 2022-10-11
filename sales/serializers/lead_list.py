from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework.response import Response

from ..models import lead_list


class PhoneContactsSerializer(serializers.ModelSerializer):
    class Meta:
        model = lead_list.PhoneOfContact
        fields = '__all__'


class ContactTypesSerializer(serializers.ModelSerializer):
    class Meta:
        model = lead_list.ContactType
        fields = ('name', )


class ContactsSerializer(serializers.ModelSerializer):
    phone_contact = PhoneContactsSerializer(
        'contact', many=True, allow_null=True)
    contact_type = ContactTypesSerializer(
        'contact', many=True, allow_null=True)

    class Meta:
        model = lead_list.Contact
        fields = '__all__'


class ActivitiesSerializer(serializers.ModelSerializer):
    class Meta:
        model = lead_list.Activities
        fields = '__all__'
        extra_kwargs = {'lead': {'required': False},
                        'user_create': {'required': False},
                        'user_update': {'required': False}}

    def validate(self):
        pk_lead = self.context['request'].__dict__[
            'parser_context']['kwargs']['pk_lead']
        if not lead_list.LeadDetail.objects.exists(pk=pk_lead):
            raise serializers.ValidationError('Lead not found')
        return self.validated_data

    def create(self, validated_data):
        pk_lead = self.context['request'].__dict__[
            'parser_context']['kwargs']['pk_lead']
        activities = lead_list.Activities.objects.create(lead_id=pk_lead, user_create=self.context['request'].user,
                                                         user_update=self.context['request'].user, **validated_data)
        return activities


class LeadDetailSerializer(serializers.ModelSerializer):

    class Meta:
        model = lead_list.LeadDetail
        fields = '__all__'


class LeadDetailCreateSerializer(serializers.ModelSerializer):
    activities = ActivitiesSerializer('lead', many=True, allow_null=True)
    contacts = ContactsSerializer('lead', many=True, allow_null=True)

    class Meta:
        model = lead_list.LeadDetail
        fields = '__all__'
