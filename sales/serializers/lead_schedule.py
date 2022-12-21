import uuid
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from rest_framework import serializers

from api.serializers.auth import UserSerializer
from base.serializers import base
from api.serializers.base import SerializerMixin
from ..models import lead_schedule
from base.utils import pop
from ..models.lead_schedule import TagSchedule, ToDo, CheckListItems, Messaging, CheckListItemsTemplate, \
    TodoTemplateChecklistItem


class ScheduleAttachmentsModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = lead_schedule.Attachments
        fields = '__all__'


class AttachmentsDailyLogModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = lead_schedule.AttachmentDailyLog
        fields = '__all__'


# class FileChecklistModelSerializer(FileSerializerMixin, serializers.ModelSerializer):
#     class Meta:
#         model = lead_schedule.FileCheckListItems
#         fields = '__all__'


class ScheduleAttachmentsSerializer(serializers.Serializer):
    file = serializers.FileField()


class MessagingSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)

    class Meta:
        model = lead_schedule.Messaging
        fields = ('id', 'message')


class TagScheduleSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)

    class Meta:
        model = lead_schedule.TagSchedule
        fields = ('id', 'name')


class CheckListItemSerializer(serializers.Serializer):
    # file = serializers.FileField(required=False)

    class Meta:
        model = lead_schedule.CheckListItems
        fields = ('to_do', 'uuid', 'parent_uuid', 'description', 'is_check', 'is_root', 'assigned_to')


class ToDoChecklistItemSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)
    assigned_to = base.IDAndNameSerializer(allow_null=True, required=False, many=True)

    # messaging = MessagingSerializer(many=True, allow_null=True)

    class Meta:
        model = lead_schedule.CheckListItems
        fields = ('id', 'parent_uuid', 'description', 'is_check', 'is_root', 'assigned_to', 'to_do', 'uuid')

    def create(self, validated_data):
        request = self.context['request']
        data = request.data
        user_create = user_update = request.user
        assigned_to = pop(data, 'assigned_to', [])
        todo = pop(data, 'to_do', None)
        data_uuid = uuid.uuid4()
        user = get_user_model().objects.filter(pk__in=[at['id'] for at in assigned_to])
        checklist_item_create = CheckListItems.objects.create(
            user_create=user_create, user_update=user_update,
            uuid=data_uuid,
            to_do_id=todo, **data
        )
        checklist_item_create.assigned_to.add(*user)
        checklist_item_template = CheckListItemsTemplate.objects.create(
            user_create=user_create, user_update=user_update,
            uuid=data_uuid,
            todo_id=todo, **data
        )
        checklist_item_template.assigned_to.add(*user)
        return checklist_item_create

    def update(self, instance, data):
        assigned_to = pop(data, 'assigned_to', [])
        todo = pop(data, 'to_do', None)
        checklist_item = lead_schedule.CheckListItems.objects.filter(pk=instance.pk)
        checklist_item.update(**data)
        checklist_item = checklist_item.first()
        uuid = checklist_item.uuid

        checklist_item_template = lead_schedule.CheckListItemsTemplate.objects.filter(todo=todo.id, uuid=uuid,
                                                                                      to_do_checklist_template=None)
        checklist_item_template.update(**data)
        checklist_item_template = checklist_item_template.first()

        # assigned_to
        user = get_user_model().objects.filter(pk__in=[tmp.get('id') for tmp in assigned_to])
        checklist_item.assigned_to.clear()
        checklist_item.assigned_to.add(*user)

        checklist_item_template.assigned_to.clear()
        checklist_item_template.assigned_to.add(*user)
        instance.refresh_from_db()
        return instance


class ToDoCreateSerializer(serializers.ModelSerializer):
    # check_list = serializers.JSONField()
    # file = serializers.FileField()
    # check_list = ToDoChecklistItemSerializer(many=True, allow_null=True)

    temp_checklist = list()
    # lead = base.IDAndNameSerializer(allow_null=True, required=False)
    assigned_to = base.IDAndNameSerializer(allow_null=True, required=False, many=True)
    tags = base.IDAndNameSerializer(allow_null=True, required=False, many=True)

    class Meta:
        model = lead_schedule.ToDo
        fields = '__all__'
        # exclude = ('lead_list',)

    def create(self, validated_data):
        request = self.context['request']

        data = request.data
        # file = data['check_list.file']
        # file_name = uuid.uuid4().hex + '.' + file.name.split('.')[-1]
        # content_file = ContentFile(file.read(), name=file_name)

        user_create = user_update = request.user
        data_checklist = pop(data, 'check_list', [])
        messaging = pop(data, 'messaging', [])
        tags = pop(data, 'tags', [])
        assigned_to = pop(data, 'assigned_to', [])
        lead_list = pop(data, 'lead_list', None)
        data_todo = data
        todo_create = ToDo.objects.create(
            user_create=user_create, user_update=user_update,
            lead_list_id=lead_list, **data_todo
        )
        tags_objects = TagSchedule.objects.filter(pk__in=[tag['id'] for tag in tags])
        user = get_user_model().objects.filter(pk__in=[at['id'] for at in assigned_to])
        todo_create.tags.add(*tags_objects)
        todo_create.assigned_to.add(*user)

        # for checklist in data_checklist:
        #     # files = pop(checklist, 'files', [])
        #     assigned_to_checklist = pop(checklist, 'assigned_to', [])
        #     create_checklist = CheckListItems.objects.create(
        #         user_create=user_create,
        #         user_update=user_update,
        #         to_do=todo_create,
        #         **checklist
        #     )
        #     user = get_user_model().objects.filter(pk__in=[tmp['id'] for tmp in assigned_to_checklist])
        #     create_checklist.assigned_to.add(*user)
        #
        # data_create_messaging = list()
        # for message in messaging:
        #     rs_message = Messaging(
        #         message=message['message'],
        #         to_do=todo_create,
        #         user_create=user_create,
        #         user_update=user_update
        #     )
        #     data_create_messaging.append(rs_message)
        # Messaging.objects.bulk_create(data_create_messaging)

        return todo_create

    def update(self, instance, data):
        # check_list = pop(data, 'check_list', [])
        # messaging = pop(data, 'messaging', [])
        todo_tags = pop(data, 'tags', [])
        assigned_to = pop(data, 'assigned_to', [])
        to_do = lead_schedule.ToDo.objects.filter(pk=instance.pk)
        to_do.update(**data)
        to_do = to_do.first()

        # tags
        tags = lead_schedule.TagSchedule.objects.filter(pk__in=[tmp.id for tmp in todo_tags])
        to_do.tags.clear()
        to_do.tags.add(*tags)

        # assigned_to
        user = get_user_model().objects.filter(pk__in=[tmp.id for tmp in assigned_to])
        to_do.assigned_to.clear()
        to_do.assigned_to.add(*user)

        # for message in messaging:
        #     data_message = lead_schedule.Messaging.objects.filter(pk=message['id'])
        #     data_message.update(message=message['message'])
        #     data_message = data_message.first()
        #
        # data_checklist = lead_schedule.CheckListItems.objects.filter(to_do=to_do.id)
        # data_checklist.delete()
        # for checklist in check_list:
        #     assigned_to_checklist = pop(checklist, 'assigned_to', [])
        #     create_checklist = CheckListItems.objects.create(
        #         to_do=to_do,
        #         **checklist
        #     )
        #     user = get_user_model().objects.filter(pk__in=[tmp.id for tmp in assigned_to_checklist])
        #     create_checklist.assigned_to.add(*user)

        instance.refresh_from_db()
        return instance

    def to_representation(self, instance):
        data = super().to_representation(instance)
        rs_checklist = list(CheckListItems.objects.filter(to_do=data['id']).values())
        data['check_list'] = rs_checklist
        rs_messaging = list(Messaging.objects.filter(to_do=data['id']).values())
        data['messaging'] = rs_messaging
        return data

    # def get_checklist_item(self, checklist):
    #
    #     for idx, data_checklist in enumerate(checklist):
    #         if 'is_root' in data_checklist.keys() and data_checklist['is_root'] is True:
    #             rs_checklist = CheckListItems(
    #                 to_do=self.to_do,
    #                 user_create=self.user,
    #                 user_update=self.user,
    #                 description=data_checklist['description'],
    #                 is_check=data_checklist['is_check'],
    #                 uuid=data_checklist['uuid'],
    #                 parent=data_checklist['uuid'],
    #                 is_root=True
    #             )
    #             self.temp_checklist.append(rs_checklist)
    #             self.parent_uuid = data_checklist['uuid']
    #             self.get_checklist_item(data_checklist['children'])
    #         else:
    #             self.children_uuid = uuid.uuid4()
    #             rs_checklist = CheckListItems(
    #                 to_do=self.to_do,
    #                 description=data_checklist['description'],
    #                 is_check=data_checklist['is_check'],
    #                 uuid=self.children_uuid,
    #                 parent=self.parent_uuid,
    #                 is_root=False
    #             )
    #             self.temp_checklist.append(rs_checklist)
    #             self.parent_uuid = self.children_uuid
    #             self.get_checklist_item(data_checklist['children'])
    #
    #     return self.temp_checklist


class DailyLogNoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = lead_schedule.DailyLogTemplateNotes
        fields = ('title', 'notes')


class DailyLogSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)

    class Meta:
        model = lead_schedule.DailyLog
        fields = ('id', 'date', 'tags', 'to_do', 'note', 'lead_list')

    def create(self, validated_data):
        request = self.context['request']
        data = request.data
        user_create = user_update = request.user
        tags = pop(data, 'tags', [])
        to_do = pop(data, 'to_do', [])
        lead_list = pop(data, 'lead_list', None)

        daily_log_create = lead_schedule.DailyLog.objects.create(
            user_create=user_create, user_update=user_update, lead_list_id=lead_list,
            **data
        )
        tags_objects = TagSchedule.objects.filter(pk__in=[tag for tag in tags])
        todo_objects = ToDo.objects.filter(pk__in=[tmp for tmp in to_do])

        daily_log_create.tags.add(*tags_objects)
        daily_log_create.to_do.add(*todo_objects)
        return daily_log_create

    def update(self, instance, data):
        to_do = pop(data, 'to_do', [])
        daily_log_tags = pop(data, 'tags', [])
        daily_log = lead_schedule.DailyLog.objects.filter(pk=instance.pk)
        daily_log.update(**data)
        daily_log = daily_log.first()

        # tags
        tags_objects = TagSchedule.objects.filter(pk__in=[tag.id for tag in daily_log_tags])
        daily_log.tags.clear()
        daily_log.tags.add(*tags_objects)

        # to_do
        todo_objects = ToDo.objects.filter(pk__in=[tmp.id for tmp in to_do])
        daily_log.to_do.clear()
        daily_log.to_do.add(*todo_objects)

        instance.refresh_from_db()
        return instance


class CheckListItemsTemplateSerializer(serializers.ModelSerializer, SerializerMixin):
    id = serializers.CharField(required=False)
    assigned_to = UserSerializer(allow_null=True, required=False, many=True)

    class Meta:
        model = lead_schedule.CheckListItemsTemplate
        fields = (
            'id', 'parent_uuid', 'description', 'is_check', 'is_root', 'assigned_to', 'todo',
            'to_do_checklist_template')

    def create(self, validated_data):
        request = self.context['request']
        data = request.data
        user_create = user_update = request.user
        assigned_to = pop(data, 'assigned_to', [])
        todo = pop(data, 'to_do', None)
        data_uuid = uuid.uuid4()
        user = get_user_model().objects.filter(pk__in=[at['id'] for at in assigned_to])
        checklist_item_template = CheckListItemsTemplate.objects.create(
            user_create=user_create, user_update=user_update,
            uuid=data_uuid,
            todo_id=todo, **data
        )
        checklist_item_template.assigned_to.add(*user)
        return checklist_item_template

    def update(self, instance, data):
        assigned_to = pop(data, 'assigned_to', [])
        todo = pop(data, 'to_do', None)

        checklist_item_template = lead_schedule.CheckListItemsTemplate.objects.filter(pk=instance.pk)
        checklist_item_template.update(**data)
        checklist_item_template = checklist_item_template.first()

        # assigned_to
        user = get_user_model().objects.filter(pk__in=[tmp.get('id') for tmp in assigned_to])
        checklist_item_template.assigned_to.clear()
        checklist_item_template.assigned_to.add(*user)
        instance.refresh_from_db()
        return instance


PASS_FIELDS = ['user_create', 'user_update', 'to_do_checklist_template']


class ToDoCheckListItemsTemplateSerializer(serializers.ModelSerializer):
    template_name = serializers.CharField(allow_null=True)
    todo = serializers.IntegerField(allow_null=True)

    class Meta:
        model = lead_schedule.TodoTemplateChecklistItem
        fields = ('id', 'template_name', 'todo')

    def create(self, validated_data):
        request = self.context['request']
        data = request.data
        user_create = user_update = request.user

        todo = pop(data, 'todo', None)

        template_to_do_checklist = lead_schedule.TodoTemplateChecklistItem.objects.create(
            user_create=user_create,
            user_update=user_update,
            **data
        )

        update_list = []
        model_checklist_item = lead_schedule.CheckListItemsTemplate.objects.filter(todo=todo,
                                                                                   to_do_checklist_template=None)
        for checklist in model_checklist_item:
            checklist.to_do_checklist_template = template_to_do_checklist
            update_list.append(checklist)

        CheckListItemsTemplate.objects.bulk_update(update_list, ['to_do_checklist_template'])
        # for checklist in checklist_item:
        #     assigned_to_checklist = pop(checklist, 'assigned_to', [])
        #
        #     create_checklist_template = lead_schedule.CheckListItemsTemplate.objects.create(
        #         user_create=user_create,
        #         user_update=user_update,
        #         to_do_checklist_template=template_to_do_checklist,
        #         **checklist
        #     )
        #
        #     user = get_user_model().objects.filter(pk__in=[tmp for tmp in assigned_to_checklist])
        #     create_checklist_template.assigned_to.add(*user)

        return template_to_do_checklist

    def update(self, instance, data):
        request = self.context['request']
        user_create = user_update = request.user
        # checklist_item = pop(data, 'checklist_item', [])
        to_do_checklist_template = lead_schedule.TodoTemplateChecklistItem.objects.filter(pk=instance.pk)
        to_do_checklist_template.update(**data)
        # to_do_checklist_template = to_do_checklist_template.first()
        #
        # data_checklist_template = lead_schedule.CheckListItemsTemplate.objects.filter(
        #     to_do_checklist_template=to_do_checklist_template.id)
        # data_checklist_template.delete()
        # for checklist in checklist_item:
        #     assigned_to_checklist = pop(checklist, 'assigned_to', [])
        #     create_checklist = lead_schedule.CheckListItemsTemplate.objects.create(
        #         to_do_checklist_template=to_do_checklist_template,
        #         user_create=user_create,
        #         user_update=user_update,
        #         **checklist
        #     )
        #     user = get_user_model().objects.filter(pk__in=[tmp.id for tmp in assigned_to_checklist])
        #     create_checklist.assigned_to.add(*user)

        instance.refresh_from_db()
        return instance


class ScheduleEventSerializer(serializers.ModelSerializer):
    # predecessors_link = PredecessorsLinkSerializer(many=True)

    class Meta:
        model = lead_schedule.ScheduleEvent
        fields = '__all__'

    def create(self, validated_data):
        request = self.context['request']
        data = request.data
        user_create = user_update = request.user
        # predecessors_link = pop(data, 'predecessors_link', [])
        assigned_user = pop(data, 'assigned_user', [])
        lead_list = pop(data, 'lead_list', None)
        viewing = pop(data, 'viewing', None)

        schedule_event_create = lead_schedule.ScheduleEvent.objects.create(
            user_create=user_create, user_update=user_update,
            lead_list_id=lead_list,
            **data
        )
        user = get_user_model().objects.filter(pk__in=[at for at in assigned_user])
        view = get_user_model().objects.filter(pk__in=[at for at in viewing])
        schedule_event_create.assigned_user.add(*user)
        schedule_event_create.viewing.add(*view)
        return schedule_event_create

    def update(self, instance, data):
        # to_predecessors_link = pop(data, 'predecessors_link', [])
        assigned_user = pop(data, 'assigned_user', [])
        viewing = pop(data, 'viewing', None)
        schedule_event = lead_schedule.ScheduleEvent.objects.filter(pk=instance.pk)
        schedule_event.update(**data)
        schedule_event = schedule_event.first()

        user = get_user_model().objects.filter(pk__in=[tmp.id for tmp in assigned_user])
        view = get_user_model().objects.filter(pk__in=[at.id for at in viewing])
        schedule_event.assigned_user.clear()
        schedule_event.assigned_user.add(*user)
        schedule_event.viewing.clear()
        schedule_event.viewing.add(*view)

        instance.refresh_from_db()
        return instance


class AttachmentsDailyLogSerializer(ScheduleAttachmentsSerializer):
    pass


class FileChecklistSerializer(ScheduleAttachmentsSerializer):
    pass