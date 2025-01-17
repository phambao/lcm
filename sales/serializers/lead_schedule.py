import datetime
from datetime import timedelta
import uuid

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.db.models import Subquery
from django.db.models import F
from django.utils import timezone
from rest_framework import serializers

from api.serializers.auth import UserCustomSerializer
from api.serializers.base import SerializerMixin
from base.serializers.base import IDAndNameSerializer
from base.serializers import base
from base.utils import pop, extra_kwargs_for_base_model
from base.constants import true, null, false
from base.views.base import remove_file
from ..models import lead_schedule, ActivitiesLog
from ..models.lead_schedule import TagSchedule, ToDo, CheckListItems, Messaging, CheckListItemsTemplate, \
    TodoTemplateChecklistItem, DataType, ItemFieldDropDown, TodoCustomField, CustomFieldScheduleSetting, \
    CustomFieldScheduleDailyLogSetting, DailyLogCustomField, ItemFieldDropDownDailyLog, \
    DataType, ItemFieldDropDown, ScheduleEventPhaseSetting, FileCheckListItems, FileCheckListItemsTemplate, \
    CommentDailyLog, AttachmentCommentDailyLog, ScheduleEventShift, Attachments, FileMessageToDo, FileMessageEvent


class EventLinkSerializer(IDAndNameSerializer):
    lead_list = serializers.IntegerField(required=False)
    is_after = serializers.BooleanField(required=False)
    is_before = serializers.BooleanField(required=False)
    due_days = serializers.IntegerField(required=False)
    end_day = serializers.DateTimeField(required=False)
    start_day = serializers.DateTimeField(required=False)


class ScheduleAttachmentsModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = lead_schedule.Attachments
        fields = '__all__'


class AttachmentsDailyLogModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = lead_schedule.AttachmentDailyLog
        fields = '__all__'


class AttachmentsEventModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = lead_schedule.FileScheduleEvent
        fields = '__all__'


class ScheduleAttachmentsSerializer(serializers.Serializer):
    file = serializers.FileField()


class FileMessageToDoSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)
    file = serializers.CharField(required=False)

    class Meta:
        model = lead_schedule.FileMessageToDo
        fields = ('id', 'message_todo', 'file', 'name')


class MessagingSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)
    notify = UserCustomSerializer(allow_null=True, required=False, many=True)
    files = FileMessageToDoSerializer(allow_null=True, required=False, many=True)

    class Meta:
        model = lead_schedule.Messaging
        fields = ('id', 'message', 'to_do', 'show_owner', 'show_sub_vendors', 'notify', 'files', 'user_create',
                  'user_update')

    def create(self, validated_data):
        request = self.context['request']
        user_create = user_update = request.user
        notify = pop(validated_data, 'notify', [])
        to_do = pop(validated_data, 'to_do', None)
        files = pop(validated_data, 'files', [])
        # files = request.FILES.getlist('files')

        schedule_todo_message_create = lead_schedule.Messaging.objects.create(
            user_create=user_create, user_update=user_update,
            to_do=to_do,
            **validated_data
        )
        file_message_todo_create = []
        for file in files:
            # file_name = uuid.uuid4().hex + '.' + file.name.split('.')[-1]
            # content_file = ContentFile(file.read(), name=file_name)
            attachment = FileMessageToDo(
                file=file['file'],
                message_todo=schedule_todo_message_create,
                user_create=user_create,
                name=file['name']
            )
            file_message_todo_create.append(attachment)
        FileMessageToDo.objects.bulk_create(file_message_todo_create)
        notify_object = get_user_model().objects.filter(pk__in=[at['id'] for at in notify])
        schedule_todo_message_create.notify.add(*notify_object)
        return schedule_todo_message_create

    def update(self, instance, data):
        request = self.context['request']
        user_create = user_update = request.user
        notify = pop(data, 'notify', [])
        to_do = pop(data, 'to_do', None)
        files = pop(data, 'files', [])
        # files = request.FILES.getlist('files')

        schedule_todo_message = lead_schedule.Messaging.objects.filter(pk=instance.pk)
        schedule_todo_message.update(**data)
        schedule_todo_message = schedule_todo_message.first()
        notify_object = get_user_model().objects.filter(pk__in=[at['id'] for at in notify])
        schedule_todo_message.notify.add(*notify_object)
        FileMessageToDo.objects.filter(message_todo=schedule_todo_message).delete()
        file_message_todo_create = []
        for file in files:
            attachment = FileMessageToDo(
                file=file['file'],
                message_todo=schedule_todo_message,
                user_create=user_create,
                name=file['name']
            )
            file_message_todo_create.append(attachment)
        FileMessageToDo.objects.bulk_create(file_message_todo_create)

        return schedule_todo_message

    def to_representation(self, instance):
        data = super().to_representation(instance)
        file = instance.todo_message_file.all()
        rs = FileMessageToDoSerializer(file, many=True)
        data['files'] = rs.data
        return data


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
    assigned_to = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    file = serializers.FileField(required=False)
    parent_uuid = serializers.UUIDField(required=False, allow_null=True)

    class Meta:
        model = lead_schedule.CheckListItems
        fields = ('id', 'parent_uuid', 'description', 'is_check', 'is_root', 'assigned_to', 'to_do', 'uuid', 'file')

    def create(self, validated_data):
        request = self.context['request']
        user_create = user_update = request.user
        assigned_to = validated_data.pop('assigned_to', '[]')
        file = pop(validated_data, 'file', [])
        files = request.FILES.getlist('file')
        if assigned_to:
            assigned_to = eval(assigned_to)
        else:
            assigned_to = []

        todo = pop(validated_data, 'to_do', None)
        data_uuid = uuid.uuid4()
        user = get_user_model().objects.filter(pk__in=[at['id'] for at in assigned_to])
        checklist_item_create = CheckListItems.objects.create(
            user_create=user_create, user_update=user_update,
            uuid=data_uuid,
            to_do=todo, **validated_data
        )
        checklist_item_create.assigned_to.add(*user)

        checklist_item_template = CheckListItemsTemplate.objects.create(
            user_create=user_create, user_update=user_update,
            uuid=data_uuid,
            todo=todo, **validated_data
        )
        checklist_item_template.assigned_to.add(*user)
        file_checklist_item_create = list()
        file_checklist_item_template_create = list()
        for file in files:
            file_name = uuid.uuid4().hex + '.' + file.name.split('.')[-1]
            content_file = ContentFile(file.read(), name=file_name)
            attachment = FileCheckListItems(
                file=content_file,
                checklist_item=checklist_item_create,
                user_create=user_create,
                name=file.name
            )
            attachment_template = FileCheckListItemsTemplate(
                file=content_file,
                checklist_item_template=checklist_item_template,
                user_create=user_create,
                name=file.name
            )
            file_checklist_item_create.append(attachment)
            file_checklist_item_template_create.append(attachment_template)
        FileCheckListItems.objects.bulk_create(file_checklist_item_create)
        FileCheckListItemsTemplate.objects.bulk_create(file_checklist_item_template_create)
        return checklist_item_create

    def update(self, instance, data):
        request = self.context['request']
        user_update = request.user
        todo = pop(data, 'to_do', None)
        assigned_to = data.pop('assigned_to', '[]')
        file = pop(data, 'file', [])
        files = request.FILES.getlist('file')
        if assigned_to:
            assigned_to = eval(assigned_to)
        else:
            assigned_to = []
        checklist_item = lead_schedule.CheckListItems.objects.filter(pk=instance.pk)
        checklist_item.update(**data)
        checklist_item = checklist_item.first()
        data_uuid = checklist_item.uuid

        checklist_item_template = lead_schedule.CheckListItemsTemplate.objects.filter(todo=todo.id, uuid=data_uuid,
                                                                                      to_do_checklist_template=None)
        checklist_item_template.update(**data)
        checklist_item_template = checklist_item_template.first()

        # assigned_to
        user = get_user_model().objects.filter(pk__in=[tmp.get('id') for tmp in assigned_to])
        checklist_item.assigned_to.clear()
        checklist_item.assigned_to.add(*user)

        checklist_item_template.assigned_to.clear()
        checklist_item_template.assigned_to.add(*user)

        # FileCheckListItems.objects.filter(checklist_item=checklist_item.id).delete()
        # FileCheckListItemsTemplate.objects.filter(checklist_item_template=checklist_item_template.id).delete()
        file_checklist_item_create = list()
        file_checklist_item_template_create = list()
        for file in files:
            file_name = uuid.uuid4().hex + '.' + file.name.split('.')[-1]
            content_file = ContentFile(file.read(), name=file_name)
            attachment = FileCheckListItems(
                file=content_file,
                checklist_item=checklist_item,
                user_update=user_update,
                name=file.name
            )
            attachment_template = FileCheckListItemsTemplate(
                file=content_file,
                checklist_item_template=checklist_item_template,
                user_update=user_update,
                name=file.name
            )
            file_checklist_item_create.append(attachment)
            file_checklist_item_template_create.append(attachment_template)
        FileCheckListItems.objects.bulk_create(file_checklist_item_create)
        FileCheckListItemsTemplate.objects.bulk_create(file_checklist_item_template_create)
        instance.refresh_from_db()
        return instance

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data_file = FileCheckListItems.objects.filter(checklist_item=data['id']).values()
        data['assigned_to'] = UserCustomSerializer(instance.assigned_to.all(), many=True).data
        data['files'] = data_file
        return data


class ToDoCreateSerializer(serializers.ModelSerializer):
    # temp_checklist = list()
    check_list = ToDoChecklistItemSerializer('check_list', allow_null=True, required=False, many=True)
    assigned_to = UserCustomSerializer(allow_null=True, required=False, many=True)
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
        event = pop(data, 'event', None)
        daily_log = pop(data, 'daily_log', None)
        data_todo = data
        todo_create = ToDo.objects.create(
            user_create=user_create, user_update=user_update,
            lead_list_id=lead_list, event_id=event, daily_log_id=daily_log, **data_todo
        )
        tags_objects = TagSchedule.objects.filter(pk__in=[tag['id'] for tag in tags])
        user = get_user_model().objects.filter(pk__in=[at['id'] for at in assigned_to])
        todo_create.tags.add(*tags_objects)
        todo_create.assigned_to.add(*user)
        duration = 0
        if validated_data['due_date']:
            duration = validated_data['due_date'] - timezone.now()
            duration = duration.days
            if duration == 0:
                duration = 1
        activities_log = ActivitiesLog.objects.create(
            title=validated_data['title'],
            type=ActivitiesLog.Type.TODO,
            duration=duration,
            start_date=timezone.now(),
            end_date=validated_data['due_date'],
            lead=validated_data['lead_list'],
            type_id=todo_create.id
        )
        activities_log.assigned_to.add(*user)

        return todo_create

    def update(self, instance, data):
        check_list = pop(data, 'check_list', [])
        messaging = pop(data, 'messaging', [])
        todo_tags = pop(data, 'tags', [])
        assigned_to = pop(data, 'assigned_to', [])
        to_do = lead_schedule.ToDo.objects.filter(pk=instance.pk)
        to_do.update(**data)
        to_do = to_do.first()

        # tags
        tags = lead_schedule.TagSchedule.objects.filter(pk__in=[tmp['id'] for tmp in todo_tags])
        to_do.tags.clear()
        to_do.tags.add(*tags)

        # assigned_to
        user = get_user_model().objects.filter(pk__in=[tmp['id'] for tmp in assigned_to])
        to_do.assigned_to.clear()
        to_do.assigned_to.add(*user)
        instance.refresh_from_db()

        activities_log = ActivitiesLog.objects.get(type_id=instance.id, type=ActivitiesLog.Type.TODO)
        activities_log.title = instance.title
        duration = activities_log.duration
        if instance.due_date:
            data_duration = instance.due_date - activities_log.start_date
            duration = data_duration.days
            if data_duration == 0:
                duration = 1
        activities_log.duration = duration
        activities_log.end_date = instance.due_date
        activities_log.assigned_to.clear()
        activities_log.assigned_to.add(*user)
        activities_log.save()
        return instance

    def to_representation(self, instance):
        data = super().to_representation(instance)
        rs_checklist = ToDoChecklistItemSerializer(instance.check_list.all(), many=True).data
        data['check_list'] = rs_checklist

        rs_messaging = MessagingSerializer(instance.messaging.all(), many=True).data
        data['messaging'] = rs_messaging
        data['custom_field'] = ToDoCustomField(instance.custom_filed_to_do.all(), many=True).data
        data['files'] = ScheduleAttachmentsModelSerializer(instance.attachments.all(), many=True).data

        return data


class ToDoCustomField(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)

    class Meta:
        model = lead_schedule.TodoCustomField
        fields = '__all__'


class MessageAndCustomFieldToDoCreateSerializer(serializers.Serializer):
    todo = serializers.IntegerField(required=False)

    custom_field = ToDoCustomField(required=False, many=True)
    message = MessagingSerializer(required=False, many=True)


class DailyLogNoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = lead_schedule.DailyLogTemplateNotes
        fields = ('id', 'title', 'notes')


class DailyLogCustomFieldSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)

    class Meta:
        model = lead_schedule.DailyLogCustomField
        fields = '__all__'


class DailyLogSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)
    custom_field = DailyLogCustomFieldSerializer(required=False, many=True)
    tags = base.IDAndNameSerializer(allow_null=True, required=False, many=True)
    to_dos = base.IDAndNameSerializer(allow_null=True, required=False, many=True)

    class Meta:
        model = lead_schedule.DailyLog
        fields = ('id', 'date', 'tags', 'to_dos', 'note', 'lead_list', 'internal_user_share', 'internal_user_notify',
                  'sub_member_share', 'sub_member_notify', 'owner_share', 'owner_notify', 'private_share',
                  'private_notify', 'custom_field', 'to_do', 'event', 'title', 'color', 'user_create', 'user_update')
        kwargs = {'to_dos': {'required': False},
                  'tags': {'required': False},
                  }

    def create(self, validated_data):
        request = self.context['request']
        user_create = user_update = request.user
        tags = pop(validated_data, 'tags', [])
        to_dos = pop(validated_data, 'to_dos', [])
        data_custom_field = pop(validated_data, 'custom_field', [])
        lead_list = pop(validated_data, 'lead_list', None)
        to_do = pop(validated_data, 'to_do', None)
        event = pop(validated_data, 'event', None)

        daily_log_create = lead_schedule.DailyLog.objects.create(
            user_create=user_create, user_update=user_update, lead_list=lead_list,
            to_do=to_do, event=event,
            **validated_data
        )
        tags_objects = TagSchedule.objects.filter(pk__in=[tag['id'] for tag in tags])
        todo_objects = ToDo.objects.filter(pk__in=[tmp['id'] for tmp in to_dos])
        daily_log_create.tags.add(*tags_objects)
        daily_log_create.to_dos.add(*todo_objects)
        data_insert = list()
        for custom_field in data_custom_field:
            temp = DailyLogCustomField(
                daily_log=daily_log_create,
                label=custom_field['label'],
                data_type=custom_field['data_type'],
                required=custom_field['required'],
                include_in_filters=custom_field['include_in_filters'],
                display_order=custom_field['display_order'],
                tool_tip_text=custom_field['tool_tip_text'],
                show_owners=custom_field['show_owners'],
                allow_permitted_sub=custom_field['allow_permitted_sub'],
                value=custom_field['value'],
                value_date=custom_field['value_date'],
                value_checkbox=custom_field['value_checkbox'],
                value_number=custom_field['value_number'],
                custom_field=custom_field['custom_field']
            )
            data_insert.append(temp)
        DailyLogCustomField.objects.bulk_create(data_insert)

        duration = 0
        if validated_data['date']:
            duration = validated_data['date'] - timezone.now()
            duration = duration.days
            if duration == 0:
                duration = 1
        activities_log = ActivitiesLog.objects.create(
            title=validated_data['title'],
            type=ActivitiesLog.Type.DAILY_LOG,
            duration=duration,
            start_date=timezone.now(),
            end_date=validated_data['date'],
            lead=lead_list,
            type_id=daily_log_create.id
        )

        return daily_log_create

    def update(self, instance, data):
        to_dos = pop(data, 'to_dos', [])
        to_do = pop(data, 'to_do', None)
        daily_log_tags = pop(data, 'tags', [])
        data_custom_field = pop(data, 'custom_field', [])
        daily_log = lead_schedule.DailyLog.objects.filter(pk=instance.pk)
        daily_log.update(**data)
        daily_log = daily_log.first()

        # tags
        tags_objects = TagSchedule.objects.filter(pk__in=[tag['id'] for tag in daily_log_tags])
        daily_log.tags.clear()
        daily_log.tags.add(*tags_objects)

        # to_do
        todo_objects = ToDo.objects.filter(pk__in=[tmp['id'] for tmp in to_dos])
        daily_log.to_dos.clear()
        daily_log.to_dos.add(*todo_objects)
        DailyLogCustomField.objects.filter(daily_log=instance.pk).delete()
        data_insert = list()
        for custom_field in data_custom_field:
            temp = DailyLogCustomField(
                daily_log=daily_log,
                label=custom_field['label'],
                data_type=custom_field['data_type'],
                required=custom_field['required'],
                include_in_filters=custom_field['include_in_filters'],
                display_order=custom_field['display_order'],
                tool_tip_text=custom_field['tool_tip_text'],
                show_owners=custom_field['show_owners'],
                allow_permitted_sub=custom_field['allow_permitted_sub'],
                value=custom_field['value'],
                value_date=custom_field['value_date'],
                value_checkbox=custom_field['value_checkbox'],
                value_number=custom_field['value_number'],
                custom_field=custom_field['custom_field']
            )
            data_insert.append(temp)
        DailyLogCustomField.objects.bulk_create(data_insert)
        instance.refresh_from_db()

        activities_log = ActivitiesLog.objects.get(type_id=instance.id, type=ActivitiesLog.Type.DAILY_LOG)
        activities_log.title = instance.title
        duration = 1
        if data['date']:
            duration = instance.date - activities_log.start_date
            duration = duration.days
            if duration == 0:
                duration = 1
        activities_log.duration = duration
        activities_log.end_date = instance.date
        activities_log.assigned_to.clear()
        activities_log.save()
        return instance

    def to_representation(self, instance):
        data = super().to_representation(instance)
        rs_custom_field = DailyLogCustomField.objects.filter(daily_log=data['id']).values()
        comments = CommentDailyLog.objects.filter(daily_log=data['id'])
        rs = CommentDailyLogSerializer(comments, many=True)
        data['custom_field'] = rs_custom_field
        data['comments'] = rs.data
        # comment = instance.comment_daily_log.all()
        # rs = CommentDailyLogSerializer(comment, many=True)
        # data['comments'] = rs.data
        return data


class FileCommentDailyLogSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)
    file = serializers.CharField(required=False)

    class Meta:
        model = lead_schedule.AttachmentCommentDailyLog
        fields = '__all__'


class CommentDailyLogSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)
    files = FileCommentDailyLogSerializer(allow_null=True, required=False, many=True)
    notify = UserCustomSerializer(allow_null=True, required=False, many=True)

    # show_sub_vendors = serializers.CharField(required=False)
    # show_owner = serializers.CharField(required=False)

    class Meta:
        model = lead_schedule.CommentDailyLog
        fields = ('daily_log', 'comment', 'files', 'id', 'user_create', 'user_update', 'show_owner', 'show_sub_vendors',
                  'notify')

    def create(self, validated_data):
        request = self.context['request']
        user_create = user_update = request.user
        daily_log = pop(validated_data, 'daily_log', None)
        notify = pop(validated_data, 'notify', [])
        files = pop(validated_data, 'files', [])
        # files = request.FILES.getlist('files')

        # if notify:
        #     notify = eval(notify)
        # else:
        #     notify = []
        #
        # if show_owner == 'True':
        #     show_owner = True
        #
        # elif show_owner == 'False':
        #     show_owner = False
        #
        # if show_sub_vendors == 'True':
        #     show_sub_vendors = True
        #
        # elif show_sub_vendors == 'False':
        #     show_sub_vendors = False

        comment_daily_log = CommentDailyLog.objects.create(
            user_create=user_create, user_update=user_update,
            daily_log=daily_log,
            **validated_data
        )
        notify_object = get_user_model().objects.filter(pk__in=[at['id'] for at in notify])
        comment_daily_log.notify.add(*notify_object)
        file_comment_daily_log_create = []
        for file in files:
            # file_name = uuid.uuid4().hex + '.' + file.name.split('.')[-1]
            # content_file = ContentFile(file.read(), name=file_name)
            attachment = AttachmentCommentDailyLog(
                file=file['file'],
                comment=comment_daily_log,
                user_create=user_create,
                name=file['name']
            )
            file_comment_daily_log_create.append(attachment)
        AttachmentCommentDailyLog.objects.bulk_create(file_comment_daily_log_create)
        return comment_daily_log

    def update(self, instance, data):
        request = self.context['request']
        user_create = user_update = request.user
        files = pop(data, 'files', [])
        notify = pop(data, 'notify', [])
        # daily_log = pop(data, 'daily_log', None)
        # files = request.FILES.getlist('files')

        comment_daily_log = CommentDailyLog.objects.filter(pk=instance.pk)
        comment_daily_log.update(**data)
        notify_object = get_user_model().objects.filter(pk__in=[at['id'] for at in notify])
        comment_daily_log = comment_daily_log.first()
        comment_daily_log.notify.clear()
        comment_daily_log.notify.add(*notify_object)
        AttachmentCommentDailyLog.objects.filter(comment=comment_daily_log).delete()
        file_comment_daily_log_create = []
        for file in files:
            # file_name = uuid.uuid4().hex + '.' + file.name.split('.')[-1]
            # content_file = ContentFile(file.read(), name=file_name)
            attachment = AttachmentCommentDailyLog(
                file=file['file'],
                comment=comment_daily_log,
                user_create=user_create,
                name=file['name']
            )
            file_comment_daily_log_create.append(attachment)
        AttachmentCommentDailyLog.objects.bulk_create(file_comment_daily_log_create)
        instance.refresh_from_db()
        return instance

    def to_representation(self, instance):
        data = super().to_representation(instance)
        file = instance.attachment_daily_log_comment.all()
        rs = FileCommentDailyLogSerializer(file, many=True)
        data['files'] = rs.data
        return data


class CheckListItemsTemplateSerializer(serializers.ModelSerializer, SerializerMixin):
    id = serializers.CharField(required=False)
    assigned_to = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    file = serializers.FileField(required=False)
    parent_uuid = serializers.UUIDField(required=False, allow_null=True)

    class Meta:
        model = lead_schedule.CheckListItemsTemplate
        fields = (
            'id', 'parent_uuid', 'description', 'is_check', 'is_root', 'assigned_to', 'todo',
            'to_do_checklist_template', 'uuid', 'file')

    def create(self, validated_data):
        request = self.context['request']
        user_create = user_update = request.user
        assigned_to = validated_data.pop('assigned_to', '[]')
        file = pop(validated_data, 'file', [])
        files = request.FILES.getlist('file')
        rq_uuid = pop(validated_data, 'uuid', None)
        if assigned_to:
            assigned_to = eval(assigned_to)
        else:
            assigned_to = []
        todo = pop(validated_data, 'todo', None)
        data_uuid = uuid.uuid4()
        user = get_user_model().objects.filter(pk__in=[at['id'] for at in assigned_to])
        checklist_item_template = CheckListItemsTemplate.objects.create(
            user_create=user_create, user_update=user_update,
            uuid=data_uuid,
            todo=todo, **validated_data
        )
        checklist_item_template.assigned_to.add(*user)

        file_checklist_item_template_create = list()
        for file in files:
            file_name = uuid.uuid4().hex + '.' + file.name.split('.')[-1]
            content_file = ContentFile(file.read(), name=file_name)

            attachment_template = FileCheckListItemsTemplate(
                file=content_file,
                checklist_item_template=checklist_item_template,
                user_create=user_create,
                name=file.name
            )
            file_checklist_item_template_create.append(attachment_template)
        FileCheckListItemsTemplate.objects.bulk_create(file_checklist_item_template_create)
        return checklist_item_template

    def update(self, instance, data):
        request = self.context['request']
        todo = pop(data, 'to_do', None)
        assigned_to = data.pop('assigned_to', '[]')
        file = pop(data, 'file', [])
        files = request.FILES.getlist('file')
        if assigned_to:
            assigned_to = eval(assigned_to)
        else:
            assigned_to = []
        checklist_item_template = lead_schedule.CheckListItemsTemplate.objects.filter(pk=instance.pk)
        checklist_item_template.update(**data)
        checklist_item_template = checklist_item_template.first()

        # assigned_to
        user = get_user_model().objects.filter(pk__in=[tmp.get('id') for tmp in assigned_to])
        checklist_item_template.assigned_to.clear()
        checklist_item_template.assigned_to.add(*user)
        file_checklist_item_template_create = list()
        for file in files:
            file_name = uuid.uuid4().hex + '.' + file.name.split('.')[-1]
            content_file = ContentFile(file.read(), name=file_name)

            attachment_template = FileCheckListItemsTemplate(
                file=content_file,
                checklist_item_template=checklist_item_template,
                name=file.name
            )
            file_checklist_item_template_create.append(attachment_template)
        FileCheckListItemsTemplate.objects.bulk_create(file_checklist_item_template_create)
        instance.refresh_from_db()
        return instance

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data_file = FileCheckListItemsTemplate.objects.filter(checklist_item_template=data['id'])
        data['assigned_to'] = UserCustomSerializer(instance.assigned_to.all(), many=True).data
        data['files'] = FileCheckListItemsTemplateSerializer(data_file, many=True).data
        return data


PASS_FIELDS = ['user_create', 'user_update', 'to_do_checklist_template']


class FileCheckListItemsTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = lead_schedule.FileCheckListItemsTemplate
        fields = '__all__'


class ToDoCheckListItemsTemplateSerializer(serializers.ModelSerializer):
    template_name = serializers.CharField(allow_null=True)
    to_do = serializers.IntegerField(allow_null=True)

    class Meta:
        model = lead_schedule.TodoTemplateChecklistItem
        fields = ('id', 'template_name', 'to_do')

    def create(self, validated_data):
        request = self.context['request']
        data = request.data
        user_create = user_update = request.user

        todo = pop(data, 'to_do', None)

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
        return template_to_do_checklist

    def update(self, instance, data):
        request = self.context['request']
        user_create = user_update = request.user
        todo = pop(data, 'to_do', None)
        # checklist_item = pop(data, 'checklist_item', [])
        to_do_checklist_template = lead_schedule.TodoTemplateChecklistItem.objects.filter(pk=instance.pk)
        to_do_checklist_template.update(**data)

        instance.refresh_from_db()
        return instance

    def to_representation(self, instance):
        data = super().to_representation(instance)
        checklist_item = lead_schedule.CheckListItemsTemplate.objects.filter(to_do_checklist_template=data['id'])
        data['check_list'] = CheckListItemsTemplateSerializer(checklist_item, many=True).data
        return data


class NamePredecessorsSerializer(serializers.Serializer):
    id = serializers.IntegerField(required=False)
    name = serializers.CharField(required=False)


class PredecessorsLinkSerializer(serializers.Serializer):
    predecessors = NamePredecessorsSerializer(allow_null=True, required=False)
    type = serializers.CharField(required=False)
    lag_day = serializers.IntegerField(required=False)


class ScheduleEventShiftReasonSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)

    class Meta:
        model = lead_schedule.EventShiftReason
        fields = ('shift_reason', 'shift_note', 'id')


class ScheduleEventShiftSerializer(serializers.ModelSerializer):
    class Meta:
        model = lead_schedule.ScheduleEventShift
        fields = ('user', 'start_day', 'start_day_after_change', 'end_day', 'end_day_after_change', 'source',
                  'notes', 'reason', 'is_direct')


class EventForInvoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = lead_schedule.ScheduleEvent
        fields = ('id', 'due_days', 'is_before', 'is_after', 'end_day', 'end_hour')


class ScheduleEventSerializer(serializers.ModelSerializer):
    links = PredecessorsLinkSerializer(required=False, many=True)
    predecessor_id = serializers.IntegerField(required=False, allow_null=True)
    viewing = UserCustomSerializer(allow_null=True, required=False, many=True)
    tags = base.IDAndNameSerializer(allow_null=True, required=False, many=True)
    assigned_user = UserCustomSerializer(allow_null=True, required=False, many=True)
    shift = ScheduleEventShiftSerializer(allow_null=True, required=False, many=True)

    class Meta:
        model = lead_schedule.ScheduleEvent
        fields = ('id', 'lead_list', 'event_title', 'assigned_user', 'reminder', 'start_day', 'end_day', 'due_days',
                  'time', 'viewing', 'notes', 'internal_notes', 'sub_notes', 'owner_notes', 'links', 'is_hourly',
                  'start_hour', 'end_hour', 'is_before', 'is_after', 'predecessor_id', 'type', 'lag_day',
                  'link_to_outside_calendar', 'tags', 'phase_label', 'phase_display_order', 'phase_color',
                  'phase_setting', 'todo', 'daily_log', 'color', 'shift', 'user_create', 'created_date',
                  'modified_date', 'user_update', 'company', 'time_reminder', 'type_time', 'jobs', 'proposal')

        extra_kwargs = {**extra_kwargs_for_base_model()}

    def create(self, validated_data):
        request = self.context['request']
        # data = request.data
        user_create = user_update = request.user
        predecessor_id = pop(validated_data, 'predecessor_id', None)
        phase_setting = pop(validated_data, 'phase_setting', None)
        links = pop(validated_data, 'links', [])
        assigned_user = pop(validated_data, 'assigned_user', [])
        lead_list = pop(validated_data, 'lead_list', None)
        viewing = pop(validated_data, 'viewing', [])
        tags = pop(validated_data, 'tags', [])
        todo = pop(validated_data, 'todo', None)
        daily_log = pop(validated_data, 'daily_log', None)
        shift = pop(validated_data, 'shift', [])
        schedule_event_create = lead_schedule.ScheduleEvent.objects.create(
            user_create=user_create, user_update=user_update,
            lead_list=lead_list,
            predecessor_id=predecessor_id,
            phase_setting=phase_setting,
            todo=todo,
            daily_log=daily_log,
            **validated_data
        )
        user = get_user_model().objects.filter(pk__in=[at['id'] for at in assigned_user])
        view = get_user_model().objects.filter(pk__in=[at['id'] for at in viewing])
        tags_objects = TagSchedule.objects.filter(pk__in=[tag['id'] for tag in tags])
        schedule_event_create.tags.add(*tags_objects)
        schedule_event_create.assigned_user.add(*user)
        schedule_event_create.viewing.add(*view)
        for data in links:
            if predecessor_id == data['predecessors']['id']:
                raise serializers.ValidationError('predecessors already exist')
            data_update = {}
            data_update['predecessor'] = schedule_event_create.id
            data_update['lag_day'] = data['lag_day']
            data_update['type'] = data['type']
            schedule_event = lead_schedule.ScheduleEvent.objects.filter(pk=data['predecessors']['id'])
            schedule_event.update(**data_update)

        data_create = []
        for data_shift in shift:
            temp = ScheduleEventShift(
                user=data_shift['user'],
                start_day=data_shift['start_day'],
                start_day_after_change=data_shift['start_day_after_change'],
                end_day=data_shift['end_day'],
                end_day_after_change=data_shift['end_day_after_change'],
                source=data_shift['source'],
                reason=data_shift['reason'],
                notes=data_shift['notes'],
                event=schedule_event_create
            )
            data_create.append(temp)
        ScheduleEventShift.objects.bulk_create(data_create)

        phase = ''
        duration = validated_data['end_day'] - validated_data['start_day']
        duration = duration.days
        if duration == 0:
            duration = 1
        if schedule_event_create.phase_setting:
            phase = schedule_event_create.phase_setting.label
        activities_log = ActivitiesLog.objects.create(
            title=validated_data['event_title'],
            type=ActivitiesLog.Type.EVENT,
            duration=duration,
            start_date=validated_data['start_day'],
            end_date=validated_data['end_day'],
            lead=lead_list,
            type_id=schedule_event_create.id,
            phase=phase
        )
        activities_log.assigned_to.add(*user)
        return schedule_event_create

    def update(self, instance, data):
        # predecessor_id = pop(data, 'predecessor_id', None)
        request = self.context['request']
        user_create = user_update = request.user
        links = pop(data, 'links', [])
        assigned_user = pop(data, 'assigned_user', [])
        viewing = pop(data, 'viewing', [])
        tags = pop(data, 'tags', [])
        shift = pop(data, 'shift', [])
        start_day_update = data['start_day'] + timedelta(hours=7)
        end_day_update = data['end_day'] + timedelta(hours=7)
        data_schedule_event = lead_schedule.ScheduleEvent.objects.filter(pk=instance.pk)
        start_day = data_schedule_event.first().start_day
        end_day = data_schedule_event.first().end_day
        data_schedule_event.update(**data)
        schedule_event = data_schedule_event.first()

        user = get_user_model().objects.filter(pk__in=[tmp['id'] for tmp in assigned_user])
        view = get_user_model().objects.filter(pk__in=[at['id'] for at in viewing])
        tags_objects = TagSchedule.objects.filter(pk__in=[tag['id'] for tag in tags])
        schedule_event.tags.clear()
        schedule_event.tags.add(*tags_objects)
        schedule_event.assigned_user.clear()
        schedule_event.assigned_user.add(*user)
        schedule_event.viewing.clear()
        schedule_event.viewing.add(*view)
        lead_schedule.ScheduleEvent.objects.filter(predecessor=instance.pk).update(predecessor=None)
        for data_link in links:
            if data['predecessor_id'] == data_link['predecessors']['id']:
                raise serializers.ValidationError('predecessors already exist')
            data_update = {}
            data_update['predecessor'] = instance.pk
            data_update['lag_day'] = data_link['lag_day']
            data_update['type'] = data_link['type']
            schedule_event_link = lead_schedule.ScheduleEvent.objects.filter(pk=data_link['predecessors']['id'])
            schedule_event_link.update(**data_update)

        data_update_children = []
        if start_day_update < start_day or start_day_update > start_day or end_day_update < end_day or end_day_update > end_day:
            data_update_children = self.get_data_update_by_group(instance.pk, start_day_update, end_day_update)
        ScheduleEventShift.objects.filter(event=schedule_event).delete()
        data_create = []
        for data_shift in shift:
            temp = ScheduleEventShift(
                user=data_shift['user'],
                start_day=data_shift['start_day'],
                start_day_after_change=data_shift['start_day_after_change'],
                end_day=data_shift['end_day'],
                end_day_after_change=data_shift['end_day_after_change'],
                source=data_shift['source'],
                reason=data_shift['reason'],
                notes=data_shift['notes'],
                is_direct=data_shift['is_direct'],
                event=schedule_event
            )
            data_create.append(temp)
        ScheduleEventShift.objects.bulk_create(data_create)

        for data_update_link in data_update_children:
            schedule_event_parent = lead_schedule.ScheduleEvent.objects.get(pk=data_update_link['predecessor'].id)
            data_schedule_event_children = lead_schedule.ScheduleEvent.objects.filter(pk=data_update_link['id'])
            data_create_shift = {
                'start_day': data_update_link['start_day_shift'],
                # 'start_day_after_change': data_update_link['start_day_shift'],
                'start_day_after_change': data_update_link['start_day'],
                'end_day': data_update_link['end_day_shift'],
                'end_day_after_change': data_update_link['end_day'],
                'source': schedule_event_parent.event_title,
                'is_direct': False
            }
            data_update = {
                'start_day': data_update_link['start_day'],
                'end_day': data_update_link['end_day'],
            }
            # data_update_link.pop('id')
            data_schedule_event_children.update(**data_update)
            data_schedule_event_children = data_schedule_event_children.first()
            lead_schedule.ScheduleEventShift.objects.create(
                user_create=user_create, user_update=user_update,
                event=data_schedule_event_children,
                user=user_create,
                **data_create_shift
            )
        instance.refresh_from_db()

        activities_log = ActivitiesLog.objects.get(type_id=instance.id, type=ActivitiesLog.Type.EVENT)
        duration = instance.end_day - activities_log.start_date
        duration = duration.days
        if duration == 0:
            duration = 1
        activities_log.title = instance.event_title
        activities_log.duration = duration
        activities_log.end_date = instance.end_day
        activities_log.assigned_to.clear()
        activities_log.assigned_to.add(*user)
        activities_log.save()
        return instance

    def to_representation(self, instance):
        data = super().to_representation(instance)
        links = lead_schedule.ScheduleEvent.objects.filter(predecessor=data['id']).values()
        message = MessageEventSerialized(instance.event_message.all(), many=True).data
        # message = lead_schedule.MessageEvent.objects.filter(event=data['id']).values()

        # shift = lead_schedule.ScheduleEventShift.objects.filter(event=data['id']).values()
        data['links'] = links
        data['message'] = message
        data['shift'] = ScheduleEventShiftSerializer(instance.shift_event.all(), many=True).data
        return data

    def get_data_update_by_group(self, pk, start_day_parent, end_day_parent):
        rs = []
        event = lead_schedule.ScheduleEvent.objects.filter(predecessor=pk)
        for e in event:
            tmp = dict()
            lag_day = e.lag_day
            type_day = e.type
            working_day = e.end_day - e.start_day
            tmp['start_day_shift'] = e.start_day
            tmp['end_day_shift'] = e.end_day
            if type_day == 'finish_to_start':
                start_day = self.date_by_adding_business_days(end_day_parent, lag_day, [])
                end_day = self.date_by_adding_business_days(start_day, working_day.days, [])
                tmp['start_day'] = start_day
                tmp['end_day'] = end_day

            elif type_day == 'start_to_start':
                start_day = self.date_by_adding_business_days(start_day_parent, lag_day, [])
                end_day = self.date_by_adding_business_days(start_day, working_day.days, [])
                tmp['start_day'] = start_day
                tmp['end_day'] = end_day

            tmp['id'] = e.id
            tmp['lag_day'] = e.lag_day
            tmp['predecessor'] = e.predecessor
            rs.append(tmp)
            rs.extend(self.get_data_update_by_group(e.id, tmp['start_day'], tmp['end_day']))
        return rs

    def date_by_adding_business_days(self, from_date, add_days, holidays):
        business_days_to_add = add_days
        current_date = from_date
        while business_days_to_add > 0:
            current_date += datetime.timedelta(days=1)
            weekday = current_date.weekday()
            if weekday >= 5:  # sunday = 6
                continue
            if current_date in holidays:
                continue
            business_days_to_add -= 1
        return current_date


class FileMessageEventSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)
    file = serializers.CharField(required=False)

    class Meta:
        model = lead_schedule.FileMessageEvent
        fields = ('id', 'message_event', 'file', 'name')


class MessageEventSerialized(serializers.ModelSerializer):
    notify = UserCustomSerializer(allow_null=True, required=False, many=True)
    files = FileMessageToDoSerializer(allow_null=True, required=False, many=True)

    # show_sub_vendors = serializers.CharField(required=False)
    # show_owner = serializers.CharField(required=False)

    class Meta:
        model = lead_schedule.MessageEvent
        fields = ('event', 'message', 'show_owner', 'show_sub_vendors', 'notify', 'files', 'user_update', 'user_create')
        read_only_fields = ('user_create', 'user_update')

    def create(self, validated_data):
        request = self.context['request']
        user_create = user_update = request.user
        notify = pop(validated_data, 'notify', [])
        event = pop(validated_data, 'event', None)
        files = pop(validated_data, 'files', [])
        schedule_event_message_create = lead_schedule.MessageEvent.objects.create(
            user_create=user_create, user_update=user_update,
            event=event,
            **validated_data
        )
        file_message_event_create = []
        for file in files:
            # file_name = uuid.uuid4().hex + '.' + file.name.split('.')[-1]
            # content_file = ContentFile(file.read(), name=file_name)
            attachment = FileMessageEvent(
                file=file['file'],
                message_event=schedule_event_message_create,
                user_create=user_create,
                name=file['name']
            )
            file_message_event_create.append(attachment)
        FileMessageEvent.objects.bulk_create(file_message_event_create)
        notify_object = get_user_model().objects.filter(pk__in=[at['id'] for at in notify])
        schedule_event_message_create.notify.add(*notify_object)
        return schedule_event_message_create

    def update(self, instance, data):
        request = self.context['request']
        user_create = user_update = request.user
        notify = pop(data, 'notify', [])
        event = pop(data, 'event', None)
        files = pop(data, 'files', [])
        # files = request.FILES.getlist('files')

        schedule_event_message = lead_schedule.MessageEvent.objects.filter(pk=instance.pk)
        schedule_event_message.update(**data)
        schedule_event_message = schedule_event_message.first()
        notify_object = get_user_model().objects.filter(pk__in=[at['id'] for at in notify])
        schedule_event_message.notify.add(*notify_object)

        data_file = FileMessageEvent.objects.filter(message_event=schedule_event_message)
        remove_file(data_file, files)
        FileMessageEvent.objects.filter(message_event=schedule_event_message).delete()
        file_message_event_create = []
        for file in files:
            attachment = FileMessageEvent(
                file=file['file'],
                message_event=schedule_event_message,
                user_create=user_create,
                name=file['name']
            )
            file_message_event_create.append(attachment)
        FileMessageEvent.objects.bulk_create(file_message_event_create)

        return schedule_event_message

    def to_representation(self, instance):
        data = super().to_representation(instance)
        file = instance.file_message_event.all()
        rs = FileMessageEventSerializer(file, many=True)
        data['files'] = rs.data
        return data


class ShiftReasonSerialized(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)

    class Meta:
        model = lead_schedule.ShiftReason
        fields = ('title', 'id')


class FieldSettingSerialized(serializers.Serializer):
    label = serializers.CharField(required=True)
    data_type = serializers.CharField(required=True)
    tool_tip_text = serializers.CharField(required=False)
    required = serializers.BooleanField(default=False)
    include_in_filters = serializers.BooleanField(default=False)
    display_order = serializers.IntegerField()
    show_owners = serializers.BooleanField(default=False)
    allow_permitted_sub = serializers.BooleanField(default=False)


class TextFieldSerialized(FieldSettingSerialized):
    default_value = serializers.CharField(allow_blank=True, required=False)


class NumberFieldSerialized(FieldSettingSerialized):
    default_number = serializers.IntegerField(required=False)


class CheckboxFieldSerialized(serializers.ModelSerializer):
    default_checkbox = serializers.BooleanField(default=False)

    class Meta:
        model = lead_schedule.CustomFieldScheduleSetting
        fields = ('label', 'data_type', 'include_in_filters', 'display_order', 'show_owners',
                  'allow_permitted_sub', 'default_checkbox')


class ItemDropdownResponseSerialized(serializers.ModelSerializer):
    class Meta:
        model = lead_schedule.ItemFieldDropDownDailyLog
        fields = '__all__'


class ItemDropdownSerialized(serializers.Serializer):
    name = serializers.CharField(required=False)


class DropdownFieldSerialized(serializers.Serializer):
    default_value = serializers.CharField(allow_null=True, required=False, allow_blank=True)
    label = serializers.CharField(required=True)
    data_type = serializers.CharField(required=True)
    required = serializers.BooleanField(default=False)
    include_in_filters = serializers.BooleanField(default=False)
    display_order = serializers.IntegerField()
    show_owners = serializers.BooleanField(default=False)
    allow_permitted_sub = serializers.BooleanField(default=False)
    name_item = ItemDropdownSerialized(allow_null=True, required=False, many=True)


class DateTimeFieldSerialized(serializers.Serializer):
    default_date = serializers.DateTimeField(allow_null=True, required=False)
    label = serializers.CharField(required=True)
    data_type = serializers.CharField(required=True)
    required = serializers.BooleanField(default=False)
    include_in_filters = serializers.BooleanField(default=False)
    display_order = serializers.IntegerField()
    show_owners = serializers.BooleanField(default=False)
    allow_permitted_sub = serializers.BooleanField(default=False)


class CustomFieldScheduleSettingSerialized(serializers.ModelSerializer):
    name_item = ItemDropdownSerialized(allow_null=True, required=False, many=True)
    todo_list = IDAndNameSerializer(required=False, many=True)

    class Meta:
        model = lead_schedule.CustomFieldScheduleSetting
        fields = '__all__'

    def create(self, validated_data):
        request = self.context['request']
        name_item = pop(validated_data, 'name_item', [])
        todo_list = pop(validated_data, 'todo_list', [])
        todo_setting = pop(validated_data, 'todo_setting', None)
        user_create = user_update = request.user
        item_types = {
            DataType.SINGLE_LINE_TEXT: TextFieldSerialized,
            DataType.MULTI_LINE_TEXT: TextFieldSerialized,
            DataType.CHECKBOX: CheckboxFieldSerialized,
            DataType.DROPDOWN: DropdownFieldSerialized,
            DataType.WHOLE_NUMBER: NumberFieldSerialized,
            DataType.CURRENCY: TextFieldSerialized,
            DataType.DATE: DateTimeFieldSerialized,
            DataType.MULTI_SELECT_DROPDOWN: DropdownFieldSerialized
        }
        data_serializers = item_types.get(validated_data['data_type'])
        data_insert = data_serializers(data=validated_data)
        data_insert.is_valid(raise_exception=True)
        data_insert = dict(data_insert.validated_data)

        data_custom_field = lead_schedule.CustomFieldScheduleSetting.objects.filter(
            todo_setting=todo_setting,
            display_order=data_insert['display_order']
        )
        if data_custom_field:
            data_custom_fields = lead_schedule.CustomFieldScheduleSetting.objects.filter(
                todo_setting=todo_setting,
                display_order__gte=data_insert['display_order']
            )
            temp = data_insert['display_order']
            for custom_field in data_custom_fields:
                if custom_field.display_order == temp:
                    custom_field.display_order += 1
                    custom_field.save()
                    temp += 1

        custom_field_create = lead_schedule.CustomFieldScheduleSetting.objects.create(
            todo_setting=todo_setting,
            user_create=user_create, user_update=user_update,
            **data_insert
        )
        if validated_data['data_type'] == DataType.DROPDOWN or validated_data['data_type'] == DataType.MULTI_SELECT_DROPDOWN:

            temp = []
            for item in name_item:
                data_insert_item = ItemFieldDropDown(
                    dropdown=custom_field_create,
                    name=item['name'],
                    user_create=user_create,
                    user_update=user_update
                )
                temp.append(data_insert_item)
            ItemFieldDropDown.objects.bulk_create(temp)

        return custom_field_create

    def update(self, instance, data):
        request = self.context['request']
        name_item = pop(data, 'name_item', [])
        todo_list = pop(data, 'todo_list', [])
        data_tool_tip_text = data['tool_tip_text']
        user_create = user_update = request.user
        # item_types = {
        #     DataType.SINGLE_LINE_TEXT: TextFieldSerialized,
        #     DataType.MULTI_LINE_TEXT: TextFieldSerialized,
        #     DataType.CHECKBOX: CheckboxFieldSerialized,
        #     DataType.DROPDOWN: DropdownFieldSerialized,
        #     DataType.WHOLE_NUMBER: NumberFieldSerialized
        # }
        #
        # data_serializers = item_types.get(data['data_type'])
        # data_update = data_serializers(data=data)
        # data_update.is_valid(raise_exception=True)
        # data_update = dict(data_update.validated_data)
        data_custom_field = lead_schedule.CustomFieldScheduleSetting.objects.filter(
            todo_setting=data['todo_setting'],
            display_order=data['display_order']
        )
        if data_custom_field:
            data_custom_fields = lead_schedule.CustomFieldScheduleSetting.objects.filter(
                todo_setting=data['todo_setting'],
                display_order__gte=data['display_order']
            )
            temp = data['display_order']
            for custom_field in data_custom_fields:
                if custom_field.display_order == temp:
                    custom_field.display_order += 1
                    custom_field.save()
                    temp += 1
        data_update = data
        data_custom_field = lead_schedule.CustomFieldScheduleSetting.objects.filter(pk=instance.pk)
        data_custom_field.update(**data_update)
        custom_field_setting = data_custom_field.first()

        if data['data_type'] == DataType.DROPDOWN:
            ItemFieldDropDown.objects.filter(dropdown=instance.pk).delete()
            temp = []
            for item in name_item:
                data_insert_item = ItemFieldDropDown(
                    dropdown=custom_field_setting,
                    name=item['name'],
                    user_create=user_create,
                    user_update=user_update
                )
                temp.append(data_insert_item)
            ItemFieldDropDown.objects.bulk_create(temp)

        temp = [data['id'] for data in todo_list]
        update_list = []
        model_todo_custom_field = lead_schedule.TodoCustomField.objects.filter(todo__in=temp, custom_field=instance.pk)
        for custom_field in model_todo_custom_field:
            custom_field.label = data_update['label']
            custom_field.data_type = data_update['data_type']
            custom_field.required = data_update['required']
            custom_field.include_in_filters = data_update['include_in_filters']
            custom_field.display_order = data_update['display_order']
            custom_field.tool_tip_text = data_tool_tip_text
            custom_field.show_owners = data_update['show_owners']
            custom_field.allow_permitted_sub = data_update['allow_permitted_sub']
            update_list.append(custom_field)
        TodoCustomField.objects.bulk_update(update_list, ['label', 'data_type', 'required', 'include_in_filters',
                                                          'display_order', 'tool_tip_text', 'show_owners',
                                                          'allow_permitted_sub', 'value', 'value_date',
                                                          'value_checkbox',
                                                          'value_number'])

        return custom_field_setting

    def to_representation(self, instance):
        data = super().to_representation(instance)
        rs_item_dropdown = ItemFieldDropDown.objects.filter(dropdown=data['id']).values()
        data['name_item'] = rs_item_dropdown
        return data


class CustomFieldScheduleDailyLogSettingSerialized(serializers.ModelSerializer):
    name_item = ItemDropdownSerialized(allow_null=True, required=False, many=True)
    daily_log_list = IDAndNameSerializer(required=False, many=True)
    default_value = serializers.CharField(allow_blank=True)

    class Meta:
        model = lead_schedule.CustomFieldScheduleDailyLogSetting
        fields = '__all__'

    def create(self, validated_data):
        request = self.context['request']
        name_item = pop(validated_data, 'name_item', [])
        daily_log_list = pop(validated_data, 'daily_log_list', [])
        daily_log_setting = pop(validated_data, 'daily_log_setting', None)
        user_create = user_update = request.user
        item_types = {
            DataType.SINGLE_LINE_TEXT: TextFieldSerialized,
            DataType.MULTI_LINE_TEXT: TextFieldSerialized,
            DataType.CHECKBOX: CheckboxFieldSerialized,
            DataType.DROPDOWN: DropdownFieldSerialized,
            DataType.WHOLE_NUMBER: NumberFieldSerialized,
            DataType.CURRENCY: TextFieldSerialized,
            DataType.DATE: DateTimeFieldSerialized,
            DataType.MULTI_SELECT_DROPDOWN: DropdownFieldSerialized
        }

        data_serializers = item_types.get(validated_data['data_type'])
        data_insert = data_serializers(data=validated_data)
        data_insert.is_valid(raise_exception=True)
        data_insert = dict(data_insert.validated_data)
        data_custom_field = lead_schedule.CustomFieldScheduleDailyLogSetting.objects.filter(
            daily_log_setting=daily_log_setting,
            display_order=data_insert['display_order']
        )
        if data_custom_field:
            data_custom_fields = lead_schedule.CustomFieldScheduleDailyLogSetting.objects.filter(
                daily_log_setting=daily_log_setting,
                display_order__gte=data_insert['display_order']
            )
            temp = data_insert['display_order']
            for custom_field in data_custom_fields:
                if custom_field.display_order == temp:
                    custom_field.display_order += 1
                    custom_field.save()
                    temp += 1
        custom_field_create = lead_schedule.CustomFieldScheduleDailyLogSetting.objects.create(
            daily_log_setting=daily_log_setting,
            user_create=user_create, user_update=user_update,
            **data_insert
        )
        if validated_data['data_type'] == DataType.DROPDOWN or validated_data['data_type'] == DataType.MULTI_SELECT_DROPDOWN:
            temp = []
            for item in name_item:
                data_insert_item = ItemFieldDropDownDailyLog(
                    dropdown=custom_field_create,
                    name=item['name'],
                    user_create=user_create,
                    user_update=user_update
                )
                temp.append(data_insert_item)
            ItemFieldDropDownDailyLog.objects.bulk_create(temp)

        return custom_field_create

    def update(self, instance, data):
        request = self.context['request']
        name_item = pop(data, 'name_item', [])
        daily_log_list = pop(data, 'daily_log_list', [])
        data_tool_tip_text = data['tool_tip_text']
        user_create = user_update = request.user
        # item_types = {
        #     DataType.SINGLE_LINE_TEXT: TextFieldSerialized,
        #     DataType.MULTI_LINE_TEXT: TextFieldSerialized,
        #     DataType.CHECKBOX: CheckboxFieldSerialized,
        #     DataType.DROPDOWN: DropdownFieldSerialized,
        #     DataType.WHOLE_NUMBER: NumberFieldSerialized
        # }
        #
        # data_serializers = item_types.get(data['data_type'])
        # data_update = data_serializers(data=data)
        # data_update.is_valid(raise_exception=True)
        # data_update = dict(data_update.validated_data)
        data_custom_field = lead_schedule.CustomFieldScheduleDailyLogSetting.objects.filter(
            daily_log_setting=data['daily_log_setting'],
            display_order=data['display_order']
        )
        if data_custom_field:
            data_custom_fields = lead_schedule.CustomFieldScheduleDailyLogSetting.objects.filter(
                daily_log_setting=data['daily_log_setting'],
                display_order=data['display_order']
            )
            temp = data['display_order']
            for custom_field in data_custom_fields:
                if custom_field.display_order == temp:
                    custom_field.display_order += 1
                    custom_field.save()
                    temp += 1
        data_update = data
        data_custom_field = lead_schedule.CustomFieldScheduleDailyLogSetting.objects.filter(pk=instance.pk)
        data_custom_field.update(**data_update)
        custom_field_setting = data_custom_field.first()

        if data['data_type'] == DataType.DROPDOWN:
            ItemFieldDropDownDailyLog.objects.filter(dropdown=instance.pk).delete()
            temp = []
            for item in name_item:
                data_insert_item = ItemFieldDropDownDailyLog(
                    dropdown=custom_field_setting,
                    name=item['name'],
                    user_create=user_create,
                    user_update=user_update
                )
                temp.append(data_insert_item)
            ItemFieldDropDownDailyLog.objects.bulk_create(temp)

        temp = [data['id'] for data in daily_log_list]
        update_list = []
        model_daily_log_custom_field = lead_schedule.DailyLogCustomField.objects.filter(daily_log__in=temp,
                                                                                        custom_field=instance.pk)
        for custom_field in model_daily_log_custom_field:
            custom_field.label = data_update['label']
            custom_field.data_type = data_update['data_type']
            custom_field.required = data_update['required']
            custom_field.include_in_filters = data_update['include_in_filters']
            custom_field.display_order = data_update['display_order']
            custom_field.tool_tip_text = data_tool_tip_text
            custom_field.show_owners = data_update['show_owners']
            custom_field.allow_permitted_sub = data_update['allow_permitted_sub']
            update_list.append(custom_field)
        lead_schedule.DailyLogCustomField.objects.bulk_update(update_list,
                                                              ['label', 'data_type', 'required', 'include_in_filters',
                                                               'display_order', 'tool_tip_text', 'show_owners',
                                                               'allow_permitted_sub', 'value', 'value_date',
                                                               'value_checkbox',
                                                               'value_number'])

        return custom_field_setting

    def to_representation(self, instance):
        data = super().to_representation(instance)
        temp = ItemDropdownResponseSerialized(instance.custom_field_daily_log_drop_down.all(), many=True).data
        data['name_item'] = temp
        return data


class ScheduleToDoSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = lead_schedule.ScheduleToDoSetting
        fields = '__all__'

    def to_representation(self, instance):
        data = super().to_representation(instance)
        rs_custom_field = CustomFieldScheduleSetting.objects.filter(todo_setting=data['id']).values()
        data['custom_field'] = rs_custom_field
        return data


class ScheduleDailyLogSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = lead_schedule.ScheduleDailyLogSetting
        fields = '__all__'

    def to_representation(self, instance):
        data = super().to_representation(instance)
        rs_custom_field = CustomFieldScheduleDailyLogSetting.objects.filter(daily_log_setting=data['id']).values()
        data['custom_field'] = rs_custom_field
        return data


class ScheduleEventSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = lead_schedule.ScheduleEventSetting
        fields = '__all__'

    def to_representation(self, instance):
        data = super().to_representation(instance)
        rs_custom_field = ScheduleEventPhaseSetting.objects.filter(event_setting=data['id']).values()
        data['phases'] = rs_custom_field
        return data


class ScheduleEventPhaseSettingSerializer(serializers.ModelSerializer):
    event_list = IDAndNameSerializer(required=False, many=True)

    class Meta:
        model = lead_schedule.ScheduleEventPhaseSetting
        fields = '__all__'

    def create(self, validated_data):
        request = self.context['request']
        event_list = pop(validated_data, 'event_list', [])

        user_create = user_update = request.user
        event_phase_create = lead_schedule.ScheduleEventPhaseSetting.objects.create(
            user_create=user_create, user_update=user_update,
            **validated_data
        )

        return event_phase_create

    def update(self, instance, data):
        request = self.context['request']
        event_list = pop(data, 'event_list', [])
        user_create = user_update = request.user
        data_event_phase = lead_schedule.ScheduleEventPhaseSetting.objects.filter(pk=instance.pk)
        data_event_phase.update(**data)
        data_event_phase = data_event_phase.first()

        temp = [data['id'] for data in event_list]
        update_list = []
        model_event_phase = lead_schedule.ScheduleEvent.objects.filter(id__in=temp, phase_setting=instance.pk)
        for phase in model_event_phase:
            phase.phase_label = data['label']
            phase.phase_display_order = data['display_order']
            phase.phase_color = data['color']
            # phase.phase_setting = instance.pk
            phase.user_create = user_create
            phase.user_update = user_update
            update_list.append(phase)

        lead_schedule.ScheduleEvent.objects.bulk_update(update_list,
                                                        ['phase_label', 'phase_display_order', 'phase_color',
                                                         'user_create',
                                                         'user_update'])

        return data_event_phase


class ScheduleHolidaySerializer(serializers.ModelSerializer):
    class Meta:
        model = lead_schedule.Holiday
        fields = ('id', 'start_holiday', 'end_holiday', 'type_holiday')


class ScheduleSetupWordDaySerializer(serializers.ModelSerializer):
    setup_workday_holiday = ScheduleHolidaySerializer(allow_null=True, required=False, many=True)
    class Meta:
        model = lead_schedule.SetupWorkDay
        fields = ('id', 'setup_workday_holiday', 'start_day', 'end_day', 'time', 'is_full_day')

    def create(self, validated_data):
        request = self.context['request']
        holidays = pop(validated_data, 'setup_workday_holiday', [])

        setup_workday = lead_schedule.SetupWorkDay.objects.create(
            **validated_data
        )
        data_create = []
        for holiday in holidays:
            temp = lead_schedule.Holiday(
                setup_workday=setup_workday,
                start_holiday=holiday['start_holiday'],
                end_holiday=holiday['end_holiday'],
                type_holiday=holiday['type_holiday'],
                company=request.user.company
            )
            data_create.append(temp)
        lead_schedule.Holiday.objects.bulk_create(data_create)
        return setup_workday

    def update(self, instance, data):
        request = self.context['request']
        holidays = pop(data, 'setup_workday_holiday', [])
        super().update(instance, data)
        data_holidays = lead_schedule.Holiday.objects.filter(setup_workday=instance.pk)
        data_holidays.delete()
        data_create = []
        for holiday in holidays:
            temp = lead_schedule.Holiday(
                setup_workday=instance,
                start_holiday=holiday['start_holiday'],
                end_holiday=holiday['end_holiday'],
                type_holiday=holiday['type_holiday'],
                company=request.user.company
            )
            data_create.append(temp)

        lead_schedule.Holiday.objects.bulk_create(data_create)

        return instance


class AttachmentsDailyLogSerializer(ScheduleAttachmentsSerializer):
    pass


class FileChecklistSerializer(ScheduleAttachmentsSerializer):
    pass


class AttachmentsEventSerializer(ScheduleAttachmentsSerializer):
    pass


class FileMesageTodoSerializer(ScheduleAttachmentsSerializer):
    pass
