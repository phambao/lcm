import uuid

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from rest_framework import serializers

from api.serializers.base import SerializerMixin
from api.serializers.auth import UserSerializer, UserCustomSerializer
from ..models import lead_list
from base.utils import pop


class IDAndNameSerializer(serializers.Serializer):
    id = serializers.IntegerField(required=False)
    name = serializers.CharField(required=False)


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
        # if self.is_param_exist('pk'):
        #     if not lead_list.Contact.objects.filter(pk=kwargs['pk']).exists():
        #         raise serializers.ValidationError('Contact not found')
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
    city = IDAndNameSerializer(allow_null=True, required=False)
    state = IDAndNameSerializer(allow_null=True, required=False)
    country = IDAndNameSerializer(allow_null=True, required=False)
    phone_contacts = PhoneContactsSerializer(
        'contact', many=True, allow_null=True, required=False)
    contact_types = ContactTypeNameCustomSerializer(many=True, allow_null=True)
    lead_id = serializers.IntegerField(allow_null=True, required=False)

    class Meta:
        model = lead_list.Contact
        fields = ('id', 'first_name', 'last_name', 'gender', 'lead_id',
                  'email', 'phone_contacts', 'contact_types',
                  'street', 'city', 'state', 'zip_code', 'country', 'user_create')
        extra_kwargs = {'street': {'required': False}}

    def create(self, validated_data):
        validated_data['user_create'] = self.context['request'].user
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
            if phone_contacts:
                lead_list.PhoneOfContact.objects.bulk_create(
                    [lead_list.PhoneOfContact(contact=ct, **pct) for pct in phone_contacts]
                )
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

        instance.phone_contacts.all().delete()
        if phone_contacts:
            lead_list.PhoneOfContact.objects.bulk_create(
                [lead_list.PhoneOfContact(contact=instance, **pct) for pct in phone_contacts]
            )

        if self.is_param_exist('pk_lead'):
            if not lead_id:
                instance.leads.remove(lead_list.LeadDetail.objects.get(pk=self.get_params()['pk_lead']))
            self.update_contact_type(instance, contact_types)
            return instance

        # Contact global does not update contact type
        if lead_id:
            instance.leads.add(lead_list.LeadDetail.objects.get(pk=lead_id))

        return super().update(instance, validated_data)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        pk_lead = self.get_params()['pk_lead'] if self.is_param_exist('pk_lead') else self.context.get('pk_lead')
        if pk_lead:  # check from url leads/<int:pk_lead>/contacts/<int:pk>/
            contact_type = instance.contact_type.filter(lead_id=pk_lead).select_related('contact_type_name')
            data['contact_types'] = [{'id': ct.contact_type_name.id, 'name': ct.contact_type_name.name}
                                     for ct in contact_type if ct.contact_type_name]
        if data['phone_contacts']:
            data['phone_number'] = data['phone_contacts'][0]['phone_number']
            data['phone_type'] = data['phone_contacts'][0]['phone_type']
        return data


class ActivitiesSerializer(serializers.ModelSerializer):
    assigned_to = UserCustomSerializer('assigners', many=True)
    attendees = UserCustomSerializer('activity_attendees', many=True)

    class Meta:
        model = lead_list.Activities
        fields = '__all__'
        extra_kwargs = {'lead': {'required': False},
                        'user_create': {'required': False},
                        'user_update': {'required': False}}
        read_only_fields = ['user_create', 'user_update']

    def validate(self, validated_data):
        try:
            pk_lead = self.context['request'].__dict__[
                'parser_context']['kwargs']['pk_lead']
            if not lead_list.LeadDetail.objects.filter(pk=pk_lead).exists():
                raise serializers.ValidationError('Lead not found')
        except KeyError:
            pass
        return validated_data

    def create(self, validated_data):
        pk_lead = self.context['request'].__dict__[
            'parser_context']['kwargs']['pk_lead']
        assigned_to = pop(validated_data, 'assigned_to', [])
        attendees = pop(validated_data, 'attendees', [])
        user_ass = get_user_model().objects.filter(pk__in=[at.get('id') for at in assigned_to])
        user_att = get_user_model().objects.filter(pk__in=[at.get('id') for at in attendees])
        activities = lead_list.Activities.objects.create(lead_id=pk_lead, user_create=self.context['request'].user,
                                                         user_update=self.context['request'].user, **validated_data)
        activities.assigned_to.add(*user_ass)
        activities.attendees.add(*user_att)
        return activities

    def update(self, instance, validated_data):

        pk_lead = self.context['request'].__dict__[
            'parser_context']['kwargs']['pk_lead']
        assigned_to = pop(validated_data, 'assigned_to', [])
        attendees = pop(validated_data, 'attendees', [])

        # assigned_to
        user = get_user_model().objects.filter(pk__in=[at.get('id') for at in assigned_to])
        if user:
            instance.assigned_to.clear()
            instance.assigned_to.add(*user)

        # attendees
        user = get_user_model().objects.filter(pk__in=[at.get('id') for at in attendees])
        if user:
            instance.attendees.clear()
            instance.attendees.add(*user)

        lead_list.Activities.objects.filter(pk=instance.pk).update(**validated_data)
        instance.refresh_from_db()
        return instance


class LeadDetailSerializer(serializers.ModelSerializer):
    city = IDAndNameSerializer(allow_null=True)
    state = IDAndNameSerializer(allow_null=True)
    country = IDAndNameSerializer(allow_null=True)
    project_types = IDAndNameSerializer(many=True, allow_null=True)
    salesperson = UserCustomSerializer(many=True)

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


PASS_FIELDS = ['user_create', 'user_update', 'lead']


class LeadDetailCreateSerializer(serializers.ModelSerializer, SerializerMixin):
    activities = ActivitiesSerializer('lead', many=True, allow_null=True, required=False)
    contacts = ContactsSerializer('leads', many=True, allow_null=True, required=False)
    photos = PhotoSerializer('lead', many=True, allow_null=True, required=False)
    city = IDAndNameSerializer(allow_null=True, required=False)
    state = IDAndNameSerializer(allow_null=True, required=False)
    country = IDAndNameSerializer(allow_null=True, required=False)
    project_types = IDAndNameSerializer(many=True, allow_null=True, required=False)
    salesperson = UserCustomSerializer(many=True)

    class Meta:
        model = lead_list.LeadDetail
        fields = '__all__'
        extra_kwargs = {'street_address': {'required': False},
                        'zip_code': {'required': False}}

    def create(self, validated_data):
        request = self.context['request']
        user_create = user_update = request.user
        data = request.data
        activities = pop(data, 'activities', [])
        contacts = pop(data, 'contacts', [])
        photos = pop(data, 'photos', [])
        project_types = pop(data, 'project_types', [])
        salesperson = pop(data, 'salesperson', [])
        lead_state = pop(data, 'state', {})
        lead_city = pop(data, 'city', {})
        lead_country = pop(data, 'country', {})

        [data.pop(field) for field in PASS_FIELDS if field in data]

        ld = lead_list.LeadDetail.objects.create(city_id=lead_city.get('id'), state_id=lead_state.get('id'),
                                                 user_create=user_create, user_update=user_update,
                                                 country_id=lead_country.get('id'), **data)
        if project_types:
            pts = []
            for project_type in project_types:
                pts.append(lead_list.ProjectType.objects.get(id=project_type.get('id')))
            ld.project_types.add(*pts)

        if salesperson:
            sps = []
            for sp in salesperson:
                sps.append(get_user_model().objects.get(id=sp.get('id')))
            ld.salesperson.add(*sps)

        if activities:
            [activity.pop(field) for activity in activities for field in PASS_FIELDS if field in activity]
            for activity in activities:
                assigned_to = pop(activity, 'assigned_to', [])
                attendees = pop(activity, 'attendees', [])
                user = get_user_model().objects.filter(pk__in=[u.get('id') for u in assigned_to])
                act = lead_list.Activities.objects.create(lead=ld, **activity)
                if user:
                    act.assigned_to.add(*user)
                user = get_user_model().objects.filter(pk__in=[u.get('id') for u in attendees])
                if user:
                    act.attendees.add(user)
        if contacts:
            for contact in contacts:
                contact_types = pop(contact, 'contact_types', [])
                phones = pop(contact, 'phone_contacts', [])
                contact_id = contact.get('id', None)
                ct_state = pop(contact, 'state', {})
                ct_city = pop(contact, 'city', {})
                ct_country = pop(contact, 'country', {})
                if contact_id:
                    # If contact has exist in database
                    ct = lead_list.Contact.objects.get(id=contact_id)
                else:
                    ct = lead_list.Contact.objects.create(country_id=ct_country.get('id'), state_id=ct_state.get('id'),
                                                          city_id=ct_city.get('id'), **contact)
                ld.contacts.add(ct)
                for contact_type in contact_types:
                    ctn = lead_list.ContactTypeName.objects.get(name=contact_type['name'])
                    lead_list.ContactType.objects.create(contact=ct, lead=ld, contact_type_name=ctn)
                lead_list.PhoneOfContact.objects.bulk_create(
                    [lead_list.PhoneOfContact(contact=ct, **phone) for phone in phones])
        if photos:
            photo_id = [photo.get('id') for photo in photos]
            lead_list.Photos.objects.filter(pk__in=photo_id).update(lead=ld)
        return ld

    def update(self, instance, data):
        activities = pop(data, 'activities', [])
        project_types = pop(data, 'project_types', [])
        salesperson = pop(data, 'salesperson', [])
        user_update = pop(data, 'user_update', None)
        user_create = pop(data, 'user_create', None)
        photos = pop(data, 'photos', [])
        contacts = pop(data, 'contacts', [])
        lead_state = pop(data, 'state', {})
        lead_city = pop(data, 'city', {})
        lead_country = pop(data, 'country', {})

        ld = instance
        ld.activities.all().delete()
        if activities:
            [activity.pop(field) for activity in activities for field in PASS_FIELDS if field in activity]

            for activity in activities:
                assigned_to = pop(activity, 'assigned_to', [])
                attendees = pop(activity, 'attendees', [])
                user = get_user_model().objects.filter(pk__in=[u.get('id') for u in assigned_to])
                act = lead_list.Activities.objects.create(lead=ld, **activity)
                if user:
                    act.assigned_to.clear()
                    act.assigned_to.add(*user)
                user = get_user_model().objects.filter(pk__in=[u.get('id') for u in attendees])
                if user:
                    act.attendees.clear()
                    act.attendees.add(*user)
        ld = lead_list.LeadDetail.objects.filter(pk=instance.pk)

        ld.update(city_id=lead_city.get('id'), state_id=lead_state.get('id'),
                  country_id=lead_country.get('id'), **data)
        ld = ld.first()

        ld.project_types.clear()
        if project_types:
            pts = []
            for project_type in project_types:
                pts.append(lead_list.ProjectType.objects.get(pk=project_type.get('id')))
            ld.project_types.add(*pts)

        ld.salesperson.clear()
        if salesperson:
            sps = []
            for sp in salesperson:
                sps.append(get_user_model().objects.get(id=sp.get('id')))
            ld.salesperson.add(*sps)

        return instance


class ProjectTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = lead_list.ProjectType
        fields = '__all__'
