import uuid

from rest_framework import serializers
from ..models import lead_schedule
from base.utils import pop
from ..models.lead_schedule import TagSchedule, ToDo, CheckListItems, Messaging


class ScheduleAttachmentsSerializer(serializers.Serializer):
    file = serializers.FileField()


class MessagingSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)

    class Meta:
        model = lead_schedule.Messaging
        fields = ('id', 'message')


class TagScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = lead_schedule.ToDo
        fields = '__all__'


class ToDoCreateSerializer(serializers.ModelSerializer):
    check_list = serializers.JSONField()
    messaging = MessagingSerializer(many=True, allow_null=True)
    temp_checklist = list()

    class Meta:
        model = lead_schedule.ToDo
        fields = '__all__'

    def create(self, validated_data):
        request = self.context['request']
        data = request.data
        user_create = user_update = request.user
        data_checklist = pop(data, 'check_list', [])
        messaging = pop(data, 'messaging', [])
        tags = pop(data, 'tags', [])
        assigned_to = pop(data, 'assigned_to', None)
        data_todo = data

        todo_create = ToDo.objects.create(
            user_create=user_create, user_update=user_update,  assigned_to_id=assigned_to, **data_todo
        )

        if tags:
            tmp_tags = []
            for tag in tags:
                tmp_tags.append(TagSchedule.objects.get(id=tag))
            todo_create.tags.add(*tmp_tags)

        data_create_checklist = list()
        for checklist in data_checklist:
            rs_checklist = CheckListItems(
                to_do=todo_create,
                user_create=user_create,
                user_update=user_update,
                description=checklist['description'],
                is_check=checklist['is_check'],
                uuid=checklist['uuid'],
                parent=checklist['parent_uuid'],
                is_root=True
            )
            data_create_checklist.append(rs_checklist)

        CheckListItems.objects.bulk_create(data_create_checklist)

        data_create_messaging = list()
        for message in messaging:
            rs_message = Messaging(
                message=message['message'],
                to_do=todo_create,
                user_create=user_create,
                user_update=user_update
            )
            data_create_messaging.append(rs_message)
        Messaging.objects.bulk_create(data_create_messaging)

        return todo_create

    def update(self, instance, data):
        # todo: update check list
        check_list = pop(data, 'check_list', [])
        messaging = pop(data, 'messaging', [])
        todo_tags = pop(data, 'tags', [])
        to_do = lead_schedule.ToDo.objects.filter(pk=instance.pk)
        to_do.update(**data)
        to_do = to_do.first()
        to_do.save()
        to_do.tags.clear()
        if todo_tags:
            tags = []
            for t in todo_tags:
                tags.append(lead_schedule.TagSchedule.objects.get(id=t.id))
            to_do.tags.add(*tags)

        for message in messaging:
            data_message = lead_schedule.Messaging.objects.filter(pk=message['id'])
            data_message.update(message=message['message'])
            data_message = data_message.first()
            data_message.save()
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


class CheckListItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = lead_schedule.CheckListItems
        fields = ('to_do', 'uuid', 'parent', 'description', 'is_check', 'is_root')
