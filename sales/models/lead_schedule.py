import uuid
from django.db import models
from django.contrib.auth import get_user_model
from api.models import BaseModel
from sales.models import LeadDetail


class TagSchedule(BaseModel):
    class Meta:
        db_table = 'tag_schedule'

    name = models.CharField(max_length=64)


class Priority(models.TextChoices):
    HIGH = 'high', 'HIGH'
    NORMAL = 'normal', 'NORMAL'
    MEDIUM = 'medium', 'MEDIUM'
    LOW = 'low', 'LOW'


class ToDo(BaseModel):
    class Meta:
        db_table = 'to_do'

    # To Do information
    title = models.CharField(max_length=128)
    priority = models.CharField(max_length=128, choices=Priority.choices, default=Priority.HIGH)
    due_date = models.DateTimeField()
    time = models.IntegerField(null=True, blank=True)
    is_complete = models.BooleanField(default=False)
    sync_due_date = models.DateTimeField()
    reminder = models.IntegerField(null=True, blank=True)
    assigned_to = models.ManyToManyField(get_user_model(), related_name='todo_assigned_to',
                                         blank=True)
    tags = models.ManyToManyField(TagSchedule, related_name='to_do_tags')
    notes = models.TextField(blank=True, max_length=128)
    lead_list = models.ForeignKey(LeadDetail, on_delete=models.CASCADE, related_name='to_do_lead_list', blank=True,
                                  null=True)


class CheckListItems(BaseModel):
    class Meta:
        db_table = 'check_list_items'

    uuid = models.UUIDField(blank=True, null=True)
    parent_uuid = models.UUIDField(blank=True, null=True)
    to_do = models.ForeignKey(ToDo, on_delete=models.CASCADE, related_name='check_list')
    description = models.CharField(blank=True, max_length=128)
    assigned_to = models.ManyToManyField(get_user_model(),
                                         related_name='checklist_item_assigned_to',
                                         blank=True)
    is_check = models.BooleanField(default=False)
    is_root = models.BooleanField(default=False)


class FileCheckListItems(BaseModel):
    class Meta:
        db_table = 'file_check_list_items'

    file = models.FileField(upload_to='sales/schedule/%Y/%m/%d/')
    checklist_item = models.ForeignKey(CheckListItems, on_delete=models.CASCADE, related_name='file_check_list')


class TodoTemplateChecklistItem(BaseModel):
    class Meta:
        db_table = 'todo_template_check_list_items'

    template_name = models.CharField(blank=True, max_length=128)


class CheckListItemsTemplate(BaseModel):
    class Meta:
        db_table = 'template_check_list_items'

    uuid = models.UUIDField(blank=True, null=True)
    parent_uuid = models.UUIDField(blank=True, null=True)
    # parent_uuid = models.ForeignKey('self', related_name='child', null=True,
    #                            blank=True, on_delete=models.SET_NULL, default=None)
    description = models.CharField(blank=True, max_length=128)
    is_check = models.BooleanField(default=False)
    is_root = models.BooleanField(default=False)
    assigned_to = models.ManyToManyField(get_user_model(),
                                         related_name='checklist_item_template_assigned_to',
                                         blank=True)
    todo = models.ForeignKey(ToDo, related_name='checklist_item_template_to_do',
                             null=True, blank=True, on_delete=models.SET_NULL)
    to_do_checklist_template = models.ForeignKey(TodoTemplateChecklistItem,
                                                 on_delete=models.CASCADE,
                                                 related_name='checklist_item_to_do_template', null=True, blank=True)


#
class FileCheckListItemsTemplate(BaseModel):
    class Meta:
        db_table = 'template_file_check_list_items'

    file = models.FileField(upload_to='sales/schedule/%Y/%m/%d/')
    checklist_item_template = models.ForeignKey(CheckListItemsTemplate, on_delete=models.CASCADE,
                                                related_name='file_check_list')


class Attachments(BaseModel):
    class Meta:
        db_table = 'attachments'
        ordering = ['-modified_date']

    file = models.FileField(upload_to='sales/schedule/%Y/%m/%d/')
    to_do = models.ForeignKey(ToDo, on_delete=models.CASCADE, related_name='attachments')


class Messaging(BaseModel):
    class Meta:
        db_table = 'messaging'

    message = models.CharField(blank=True, max_length=128)
    to_do = models.ForeignKey(ToDo, on_delete=models.CASCADE, related_name='messaging')


class DailyLog(BaseModel):
    class Meta:
        db_table = 'schedule_daily_log'

    date = models.DateField()
    tags = models.ManyToManyField(TagSchedule, related_name='daily_log_tags')
    to_do = models.ManyToManyField(ToDo, related_name='daily_log_tags')
    note = models.TextField(blank=True)
    lead_list = models.ForeignKey(LeadDetail, on_delete=models.CASCADE, related_name='daily_log_lead_list')


class DailyLogTemplateNotes(BaseModel):
    class Meta:
        db_table = 'daily_log_template_note'

    title = models.CharField(blank=True, max_length=128)
    notes = models.TextField(blank=True)
    # daily_log = models.ForeignKey(DailyLog, on_delete=models.CASCADE, related_name='daily_log_note_daily_log')


class AttachmentDailyLog(BaseModel):
    class Meta:
        db_table = 'attachment_daily_log'
        ordering = ['-modified_date']

    file = models.FileField(upload_to='sales/schedule/%Y/%m/%d/')
    daily_log = models.ForeignKey(DailyLog, on_delete=models.CASCADE, related_name='attachment_daily_log_daily_log')


class ScheduleEvent(BaseModel):
    class Meta:
        db_table = 'schedule_event'

    lead_list = models.ForeignKey(LeadDetail, on_delete=models.CASCADE, related_name='schedule_event_lead_list')
    # division = models.CharField
    # project = models.CharField
    event_title = models.CharField(blank=True, max_length=128)
    assigned_user = models.ManyToManyField(get_user_model(), related_name='schedule_event_assigned_user',
                                           blank=True)
    reminder = models.IntegerField(blank=True, null=True)
    start_day = models.DateField()
    # due_day = models.DateField()
    viewing = models.ManyToManyField(get_user_model(), related_name='schedule_event_viewing',
                                     blank=True)

# class ScheduleEventPredecessorsLink(BaseModel):
#     class Meta:
#         db_table = 'schedule_event_predecessors_link'

# name_predecessors = models.ForeignKey(get_user_model(), on_delete=models.CASCADE,
#                                       related_name='schedule_event_predecessors_link_name')

# type = models.CharField(max_length=128, blank=True)
# log_day = models.DateField()
# event_schedule = models.ForeignKey(ScheduleEvent, on_delete=models.CASCADE,
#                                    related_name='predecessors_link_schedule_event')