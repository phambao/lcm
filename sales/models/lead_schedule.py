import uuid
from django.db import models

from api.models import BaseModel


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
    assigned_to = models.IntegerField(null=True, blank=True)
    tags = models.ManyToManyField(TagSchedule, related_name='to_do_tags')
    notes = models.CharField(blank=True, max_length=128)


class CheckListItems(BaseModel):
    class Meta:
        db_table = 'check_list_items'

    to_do = models.ForeignKey(ToDo, on_delete=models.CASCADE, related_name='check_list')
    uuid = models.UUIDField(default=uuid.uuid4)
    parent = models.UUIDField()
    description = models.CharField(blank=True, max_length=128)
    is_check = models.BooleanField(default=False)
    is_root = models.BooleanField(default=False)


class Attachments(BaseModel):
    class Meta:
        db_table = 'attachments'
        ordering = ['-modified_date']

    file = models.FileField(upload_to='file')
    to_do = models.ForeignKey(ToDo, on_delete=models.CASCADE, related_name='attachments')


class Messaging(BaseModel):
    class Meta:
        db_table = 'messaging'

    message = models.CharField(blank=True, max_length=128)
    to_do = models.ForeignKey(ToDo, on_delete=models.CASCADE, related_name='messaging')
