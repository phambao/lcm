import uuid

from django.contrib.auth import get_user_model
from rest_framework import serializers

from api.serializers.auth import UserSerializer
from api.serializers.base import SerializerMixin
from base.serializers.base import IDAndNameSerializer
from base.serializers import base
from base.utils import pop
from ..models import lead_schedule
from ..models.lead_schedule import TagSchedule, ToDo, CheckListItems, Messaging, CheckListItemsTemplate, \
    TodoTemplateChecklistItem, DataType, ItemFieldDropDown, TodoCustomField, CustomFieldScheduleSetting, \
    CustomFieldScheduleDailyLogSetting, DailyLogCustomField, ItemFieldDropDownDailyLog, \
    DataType, ItemFieldDropDown, ScheduleEventPhaseSetting


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
        instance.refresh_from_db()
        return instance

    def to_representation(self, instance):
        data = super().to_representation(instance)
        rs_checklist = CheckListItems.objects.filter(to_do=data['id']).values()
        data['check_list'] = rs_checklist
        rs_messaging = Messaging.objects.filter(to_do=data['id']).values()
        data['messaging'] = rs_messaging
        rs_custom_field = TodoCustomField.objects.filter(todo=data['id']).values()
        data['custom_field'] = rs_custom_field
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
        fields = ('title', 'notes')


class DailyLogCustomFieldSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)

    class Meta:
        model = lead_schedule.DailyLogCustomField
        fields = '__all__'


class DailyLogSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)
    custom_field = DailyLogCustomFieldSerializer(required=False, many=True)

    class Meta:
        model = lead_schedule.DailyLog
        fields = ('id', 'date', 'tags', 'to_do', 'note', 'lead_list', 'internal_user_share', 'internal_user_notify',
                  'sub_member_share', 'sub_member_notify', 'owner_share', 'owner_notify', 'private_share',
                  'private_notify', 'custom_field')

    def create(self, validated_data):
        request = self.context['request']
        data = request.data
        user_create = user_update = request.user
        tags = pop(data, 'tags', [])
        to_do = pop(data, 'to_do', [])
        data_custom_field = pop(data, 'custom_field', [])
        lead_list = pop(data, 'lead_list', None)

        daily_log_create = lead_schedule.DailyLog.objects.create(
            user_create=user_create, user_update=user_update, lead_list_id=lead_list,
            **data
        )
        tags_objects = TagSchedule.objects.filter(pk__in=[tag for tag in tags])
        todo_objects = ToDo.objects.filter(pk__in=[tmp for tmp in to_do])
        daily_log_create.tags.add(*tags_objects)
        daily_log_create.to_do.add(*todo_objects)
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
                custom_field_id=custom_field['custom_field']
            )
            data_insert.append(temp)
        DailyLogCustomField.objects.bulk_create(data_insert)

        return daily_log_create

    def update(self, instance, data):
        to_do = pop(data, 'to_do', [])
        daily_log_tags = pop(data, 'tags', [])
        data_custom_field = pop(data, 'custom_field', [])
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
        return instance

    def to_representation(self, instance):
        data = super().to_representation(instance)
        rs_custom_field = DailyLogCustomField.objects.filter(daily_log=data['id']).values()
        data['custom_field'] = rs_custom_field
        return data


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
        return template_to_do_checklist

    def update(self, instance, data):
        request = self.context['request']
        user_create = user_update = request.user
        # checklist_item = pop(data, 'checklist_item', [])
        to_do_checklist_template = lead_schedule.TodoTemplateChecklistItem.objects.filter(pk=instance.pk)
        to_do_checklist_template.update(**data)

        instance.refresh_from_db()
        return instance


class NamePredecessorsSerializer(serializers.Serializer):
    id = serializers.IntegerField(required=False)
    name = serializers.CharField(required=False)


class PredecessorsLinkSerializer(serializers.Serializer):
    name_predecessors = NamePredecessorsSerializer(allow_null=True, required=False)
    type = serializers.CharField(required=False)
    lag_day = serializers.IntegerField(required=False)


class ScheduleEventSerializer(serializers.ModelSerializer):
    links = PredecessorsLinkSerializer(required=False, many=True)
    predecessor_id = serializers.IntegerField(required=False, allow_null=True)
    class Meta:
        model = lead_schedule.ScheduleEvent
        fields = ('id', 'lead_list', 'event_title', 'assigned_user', 'reminder', 'start_day', 'end_day', 'due_days',
                  'time', 'viewing', 'notes', 'internal_notes', 'sub_notes', 'owner_notes', 'links',
                  'start_hour', 'end_hour', 'is_before', 'is_after', 'predecessor_id', 'type', 'lag_day',
                  'link_to_outside_calendar', 'tags', 'phase_label', 'phase_display_order', 'phase_color', 'phase_setting')

    def create(self, validated_data):
        request = self.context['request']
        data = request.data
        user_create = user_update = request.user
        predecessor_id = pop(data, 'predecessor_id', None)
        phase_setting = pop(data, 'phase_setting', None)
        links = pop(data, 'links', [])
        assigned_user = pop(data, 'assigned_user', [])
        lead_list = pop(data, 'lead_list', None)
        viewing = pop(data, 'viewing', [])
        tags = pop(data, 'tags', [])
        schedule_event_create = lead_schedule.ScheduleEvent.objects.create(
            user_create=user_create, user_update=user_update,
            lead_list_id=lead_list,
            predecessor_id=predecessor_id,
            phase_setting_id=phase_setting,
            **data
        )
        user = get_user_model().objects.filter(pk__in=[at for at in assigned_user])
        view = get_user_model().objects.filter(pk__in=[at for at in viewing])
        tags_objects = TagSchedule.objects.filter(pk__in=[tag for tag in tags])
        schedule_event_create.tags.add(*tags_objects)
        schedule_event_create.assigned_user.add(*user)
        schedule_event_create.viewing.add(*view)
        for data in links:
            data_update = {}
            data_update['predecessor'] = schedule_event_create.id
            data_update['lag_day'] = data['lag_day']
            data_update['type'] = data['type']
            schedule_event = lead_schedule.ScheduleEvent.objects.filter(pk=data['name_predecessors']['id'])
            schedule_event.update(**data_update)

        return schedule_event_create

    def update(self, instance, data):
        # predecessor_id = pop(data, 'predecessor_id', None)
        links = pop(data, 'links', [])
        assigned_user = pop(data, 'assigned_user', [])
        viewing = pop(data, 'viewing', [])
        tags = pop(data, 'tags', [])
        data_schedule_event = lead_schedule.ScheduleEvent.objects.filter(pk=instance.pk)
        data_schedule_event.update(**data)
        schedule_event = data_schedule_event.first()

        user = get_user_model().objects.filter(pk__in=[tmp.id for tmp in assigned_user])
        view = get_user_model().objects.filter(pk__in=[at.id for at in viewing])
        # tags_objects = TagSchedule.objects.filter(pk__in=[tag for tag in tags])
        schedule_event.tags.clear()
        schedule_event.tags.add(*tags)
        schedule_event.assigned_user.clear()
        schedule_event.assigned_user.add(*user)
        schedule_event.viewing.clear()
        schedule_event.viewing.add(*view)
        lead_schedule.ScheduleEvent.objects.filter(predecessor=instance.pk).update(predecessor=None)
        for data in links:
            data_update = {}
            data_update['predecessor'] = instance.pk
            data_update['lag_day'] = data['lag_day']
            data_update['type'] = data['type']
            schedule_event = lead_schedule.ScheduleEvent.objects.filter(pk=data['name_predecessors']['id'])
            schedule_event.update(**data_update)

        instance.refresh_from_db()
        return instance

    def to_representation(self, instance):
        data = super().to_representation(instance)
        links = lead_schedule.ScheduleEvent.objects.filter(predecessor=data['id']).values()
        data['links'] = links
        return data


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
    default_value = serializers.CharField(required=False)


class NumberFieldSerialized(FieldSettingSerialized):
    default_value = serializers.IntegerField(required=False)


class CheckboxFieldSerialized(serializers.ModelSerializer):
    default_value = serializers.BooleanField(default=False)

    class Meta:
        model = lead_schedule.CustomFieldScheduleSetting
        fields = ('label', 'data_type', 'include_in_filters', 'display_order', 'show_owners',
                  'allow_permitted_sub', 'default_value')


class ItemDropdownSerialized(serializers.Serializer):
    name = serializers.CharField(required=False)


class DropdownFieldSerialized(serializers.Serializer):
    default_value = serializers.CharField(required=False)
    label = serializers.CharField(required=True)
    data_type = serializers.CharField(required=True)
    required = serializers.BooleanField(default=False)
    include_in_filters = serializers.BooleanField(default=False)
    display_order = serializers.IntegerField()
    show_owners = serializers.BooleanField(default=False)
    allow_permitted_sub = serializers.BooleanField(default=False)
    name_item = ItemDropdownSerialized(allow_null=True, required=False, many=True)


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
            DataType.DROPDOWN: DropdownFieldSerialized
        }

        data_serializers = item_types.get(validated_data['data_type'])
        data_insert = data_serializers(data=validated_data)
        data_insert.is_valid(raise_exception=True)
        data_insert = dict(data_insert.validated_data)

        custom_field_create = lead_schedule.CustomFieldScheduleSetting.objects.create(
            todo_setting=todo_setting,
            user_create=user_create, user_update=user_update,
            **data_insert
        )
        if validated_data['data_type'] == DataType.DROPDOWN:
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
        item_types = {
            DataType.SINGLE_LINE_TEXT: TextFieldSerialized,
            DataType.MULTI_LINE_TEXT: TextFieldSerialized,
            DataType.CHECKBOX: CheckboxFieldSerialized,
            DataType.DROPDOWN: DropdownFieldSerialized
        }

        data_serializers = item_types.get(data['data_type'])
        data_update = data_serializers(data=data)
        data_update.is_valid(raise_exception=True)
        data_update = dict(data_update.validated_data)
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
            DataType.DROPDOWN: DropdownFieldSerialized
        }

        data_serializers = item_types.get(validated_data['data_type'])
        data_insert = data_serializers(data=validated_data)
        data_insert.is_valid(raise_exception=True)
        data_insert = dict(data_insert.validated_data)

        custom_field_create = lead_schedule.CustomFieldScheduleDailyLogSetting.objects.create(
            daily_log_setting=daily_log_setting,
            user_create=user_create, user_update=user_update,
            **data_insert
        )
        if validated_data['data_type'] == DataType.DROPDOWN:
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
        item_types = {
            DataType.SINGLE_LINE_TEXT: TextFieldSerialized,
            DataType.MULTI_LINE_TEXT: TextFieldSerialized,
            DataType.CHECKBOX: CheckboxFieldSerialized,
            DataType.DROPDOWN: DropdownFieldSerialized
        }

        data_serializers = item_types.get(data['data_type'])
        data_update = data_serializers(data=data)
        data_update.is_valid(raise_exception=True)
        data_update = dict(data_update.validated_data)
        data_custom_field = lead_schedule.CustomFieldScheduleDailyLogSetting.objects.filter(pk=instance.pk)
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
        rs_item_dropdown = ItemFieldDropDown.objects.filter(dropdown=data['id']).values()
        data['name_item'] = rs_item_dropdown
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
                                                        ['phase_label', 'phase_display_order', 'phase_color', 'user_create',
                                                         'user_update'])

        return data_event_phase


class AttachmentsDailyLogSerializer(ScheduleAttachmentsSerializer):
    pass


class FileChecklistSerializer(ScheduleAttachmentsSerializer):
    pass


class AttachmentsEventSerializer(ScheduleAttachmentsSerializer):
    pass
