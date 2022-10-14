import re
from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework.response import Response

from ..models import lead_list
from django.core.files.base import ContentFile
import uuid

class PhoneContactsSerializer(serializers.ModelSerializer):
    class Meta:
        model = lead_list.PhoneOfContact
        fields = ('id', 'phone_number', 'phone_type',
                  'text_massage_received', 'mobile_phone_service_provider')

    def validate(self, validated_data):
        pk_contact = self.context['request'].__dict__[
            'parser_context']['kwargs']['pk']
        if not lead_list.Contact.objects.filter(pk=pk_contact).exists():
            raise serializers.ValidationError('Contact not found')
        return validated_data

    def create(self, validated_data):
        pk_contact = self.context['request'].__dict__[
            'parser_context']['kwargs']['pk']
        phones = lead_list.PhoneOfContact.objects.create(contact_id=pk_contact, **validated_data)
        return phones


class ContactTypesSerializer(serializers.ModelSerializer):
    class Meta:
        model = lead_list.ContactType
        fields = ('id', 'contact_type_name', )


class ContactsSerializer(serializers.ModelSerializer):
    phone_contacts = PhoneContactsSerializer(
        'contact', many=True, allow_null=True)
    contact_type = ContactTypesSerializer(
        'contact', many=True, allow_null=True)

    class Meta:
        model = lead_list.Contact
        fields = ('id', 'first_name', 'last_name', 'gender',
                  'email', 'phone_contacts', 'contact_type',
                  'street', 'city', 'state', 'zip_code', 'country')


class ActivitiesSerializer(serializers.ModelSerializer):
    class Meta:
        model = lead_list.Activities
        fields = '__all__'
        extra_kwargs = {'lead': {'required': False},
                        'user_create': {'required': False},
                        'user_update': {'required': False}}

    def validate(self, validated_data):
        pk_lead = self.context['request'].__dict__[
            'parser_context']['kwargs']['pk_lead']
        if not lead_list.LeadDetail.objects.filter(pk=pk_lead).exists():
            raise serializers.ValidationError('Lead not found')
        return validated_data

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


class PhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = lead_list.Photos
        fields = ('id', 'photo')

    def validate(self, validated_data):
        pk_lead = self.context['request'].__dict__[
            'parser_context']['kwargs']['pk_lead']
        if not lead_list.LeadDetail.objects.filter(pk=pk_lead).exists():
            raise serializers.ValidationError('Lead not found')
        return validated_data
    
    def create(self, validated_data):
        pk_lead = self.context['request'].__dict__[
            'parser_context']['kwargs']['pk_lead']
        file = self.context['request'].FILES.get('photo')
        file_name = uuid.uuid4().hex + '.' + file.name.split('.')[-1]
        content_file = ContentFile(file.read(), name=file_name)
        photo = lead_list.Photos.objects.create(
            photo=content_file, lead_id=pk_lead)
        return photo
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['photo'] = r'(?<=/media/).+?(?=/)'.replace(r'(?<=/media/).+?(?=/)', instance.photo.url)
        print(data)
        return data


class LeadDetailCreateSerializer(serializers.ModelSerializer):
    activities = ActivitiesSerializer('lead', many=True, allow_null=True)
    contacts = ContactsSerializer('leads', many=True, allow_null=True)
    photos = PhotoSerializer('lead', many=True, allow_null=True)

    class Meta:
        model = lead_list.LeadDetail
        fields = '__all__'
