import uuid

from django.core.files.base import ContentFile
from rest_framework import serializers

from api.serializers.base import SerializerMixin
from ..models import lead_list


class IDAndNameSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()


class PhoneContactsSerializer(serializers.ModelSerializer, SerializerMixin):
    class Meta:
        model = lead_list.PhoneOfContact
        fields = ('id', 'phone_number', 'phone_type',
                  'text_massage_received', 'mobile_phone_service_provider')

    def validate(self, validated_data):
        kwargs = self.get_params()
        if self.is_param_exist('pk_lead'):
            if not lead_list.LeadDetail.objects.filter(pk=kwargs['pk_lead']).exists():
                raise serializers.ValidationError('Lead not found')
        if self.is_param_exist('pk'):
            if not lead_list.Contact.objects.filter(pk=kwargs['pk']).exists():
                raise serializers.ValidationError('Contact not found')
        return validated_data

    def create(self, validated_data):
        pk_contact = self.context['request'].__dict__[
            'parser_context']['kwargs']['pk']
        phones = lead_list.PhoneOfContact.objects.create(contact_id=pk_contact, **validated_data)
        return phones


class ContactTypeNameSerializer(serializers.ModelSerializer):
    class Meta:
        model = lead_list.ContactTypeName
        fields = '__all__'


class ContactTypesSerializer(serializers.ModelSerializer):

    class Meta:
        model = lead_list.ContactType
        fields = ('id', 'contact_type_name', )


class ContactTypeNameCustomSerializer(serializers.Serializer):
    name = serializers.CharField()


class ContactsSerializer(serializers.ModelSerializer, SerializerMixin):
    city = IDAndNameSerializer(allow_null=True)
    state = IDAndNameSerializer(allow_null=True)
    country = IDAndNameSerializer(allow_null=True)
    phone_contacts = PhoneContactsSerializer(
        'contact', many=True, allow_null=True)
    contact_types = ContactTypeNameCustomSerializer(many=True, allow_null=True)
    lead_id = serializers.IntegerField(allow_null=True, required=False)

    class Meta:
        model = lead_list.Contact
        fields = ('id', 'first_name', 'last_name', 'gender', 'lead_id',
                  'email', 'phone_contacts', 'contact_types',
                  'street', 'city', 'state', 'zip_code', 'country')

    def create(self, validated_data):
        if self.is_param_exist('pk_lead'):
            phone_contacts = validated_data.pop('phone_contacts')
            contact_types = validated_data.pop('contact_types')
            state = validated_data.pop('state')
            city = validated_data.pop('city')
            country = validated_data.pop('country')
            ct = lead_list.Contact.objects.create(country_id=country.get('id'), state_id=state.get('id'),
                                                  city_id=city.get('id'), **validated_data)
            ld = lead_list.LeadDetail.objects.get(pk=self.get_params()['pk_lead'])
            ct.leads.add(ld)
            for contact_type in contact_types:
                ctn = lead_list.ContactTypeName.objects.get(name=contact_type['name'])
                lead_list.ContactType.objects.create(contact=ct, lead=ld, contact_type_name=ctn)
            return ct
        return super().create(validated_data)

    def update_contact_type(self, instance, contact_types):
        instance.contact_type.all().delete()
        if contact_types:
            for contact_type in contact_types:
                ctn = lead_list.ContactTypeName.objects.get(name=contact_type['name'])
                lead = lead_list.LeadDetail.objects.get(pk=self.get_params()['pk_lead'])
                lead_list.ContactType.objects.create(contact=instance, lead=lead, contact_type_name=ctn)

    def update(self, instance, validated_data):
        phone_contacts = validated_data.pop('phone_contacts')
        contact_types = validated_data.pop('contact_types')
        lead_id = validated_data.pop('lead_id')
        state = validated_data.pop('state')
        city = validated_data.pop('city')
        country = validated_data.pop('country')

        instance = lead_list.Contact.objects.filter(pk=self.get_params()['pk'])
        instance.update(country_id=country.get('id'), state_id=state.get('id'),
                        city_id=city.get('id'), **validated_data)
        instance = instance.first()
        if self.is_param_exist('pk_lead'):
            if not lead_id:
                instance.leads.remove(lead_list.LeadDetail.objects.get(pk=self.get_params()['pk_lead']))
            self.update_contact_type(instance, contact_types)
            return instance

        # Contact global does not update contact type
        if lead_id:
            instance.leads.add(lead_list.LeadDetail.objects.get(pk=lead_id))

        instance.phone_contacts.all().delete()
        if phone_contacts:
            lead_list.PhoneOfContact.objects.bulk_create(
                [lead_list.PhoneOfContact(contact=instance, **pct) for pct in phone_contacts]
            )
        return super().update(instance, validated_data)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        pk_lead = self.get_params()['pk_lead'] if self.is_param_exist('pk_lead') else self.context.get('pk_lead')
        if pk_lead:  # check from url leads/<int:pk_lead>/contacts/<int:pk>/
            contact_type = instance.contact_type.filter(lead_id=pk_lead).select_related('contact_type_name')
            data['contact_types'] = [{'id': ct.contact_type_name.id, 'name': ct.contact_type_name.name}
                                     for ct in contact_type if ct.contact_type_name]
        return data


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
    city = IDAndNameSerializer(allow_null=True)
    state = IDAndNameSerializer(allow_null=True)
    country = IDAndNameSerializer(allow_null=True)

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
        return data


class LeadDetailCreateSerializer(serializers.ModelSerializer, SerializerMixin):
    activities = ActivitiesSerializer('lead', many=True, allow_null=True)
    contacts = ContactsSerializer('leads', many=True, allow_null=True)
    photos = PhotoSerializer('lead', many=True, allow_null=True)
    city = IDAndNameSerializer(allow_null=True)
    state = IDAndNameSerializer(allow_null=True)
    country = IDAndNameSerializer(allow_null=True)

    class Meta:
        model = lead_list.LeadDetail
        fields = '__all__'
