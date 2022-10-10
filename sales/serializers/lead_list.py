from django.contrib.auth import get_user_model
from rest_framework import serializers

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
    phone_contact = PhoneContactsSerializer('contact', many=True, allow_null=True)
    contact_type = ContactTypesSerializer('contact', many=True, allow_null=True)

    class Meta:
        model = lead_list.Contact
        fields = '__all__'


class ActivitiesSerializer(serializers.ModelSerializer):
    class Meta:
        model = lead_list.Activities
        fields = '__all__'


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
