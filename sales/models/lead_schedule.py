from django.contrib.auth import get_user_model
from django.db import models

from api.models import BaseModel
from base.models.config import Config
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


class Type(models.TextChoices):
    FINISH_TO_START = 'finish_to_start', 'FINISH_TO_START'
    START_TO_START = 'start_to_start', 'START_TO_START'


class BuilderView(models.TextChoices):
    CALENDAR_DAY = 'calendar-day', 'CALENDAR-DAY'
    CALENDAR_WEEK = 'calendar-week', 'CALENDAR-WEEK'
    CALENDAR_MONTH = 'calendar-month', 'CALENDAR-MONTH'
    CALENDAR_YEAR = 'calendar-year', 'CALENDAR-YEAR'
    CALENDAR_SCHEDULE = 'calendar-schedule', 'CALENDAR-SCHEDULE'


class ReminderType(models.IntegerChoices):
    NO = 0,
    YES = 1,


class ToDo(BaseModel):
    class Meta:
        db_table = 'to_do'

    # To Do information
    title = models.CharField(max_length=128)
    priority = models.CharField(max_length=128, choices=Priority.choices, default=Priority.HIGH)
    due_date = models.DateTimeField(blank=True, null=True)
    # time = models.IntegerField(null=True, blank=True)
    time_hour = models.DateTimeField(default=None, blank=True, null=True)
    is_complete = models.BooleanField(default=False)
    sync_due_date = models.DateTimeField(null=True, blank=True)
    reminder = models.IntegerField(null=True, blank=True)
    assigned_to = models.ManyToManyField(get_user_model(), related_name='todo_assigned_to',
                                         blank=True)
    tags = models.ManyToManyField(TagSchedule, related_name='to_do_tags')
    notes = models.TextField(blank=True)
    lead_list = models.ForeignKey(LeadDetail, on_delete=models.CASCADE, related_name='to_do_lead_list', blank=True,
                                  null=True)
    color = models.CharField(max_length=128, blank=True)
    event = models.ForeignKey('ScheduleEvent', on_delete=models.SET_NULL, related_name='to_do_event', blank=True,
                              null=True)
    daily_log = models.ForeignKey('DailyLog', on_delete=models.SET_NULL, related_name='to_do_daily_log', blank=True,
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
    name = models.CharField(blank=True, max_length=128, null=True)


class TodoTemplateChecklistItem(BaseModel):
    class Meta:
        db_table = 'todo_template_check_list_items'

    template_name = models.CharField(blank=True, max_length=128)


class CheckListItemsTemplate(BaseModel):
    class Meta:
        db_table = 'template_check_list_items'

    uuid = models.UUIDField(blank=True, null=True)
    parent_uuid = models.UUIDField(blank=True, null=True)
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
                                                related_name='file_check_list'),
    name = models.CharField(blank=True, max_length=128, null=True)


class Attachments(BaseModel):
    class Meta:
        db_table = 'attachments'
        ordering = ['-modified_date']

    file = models.FileField(upload_to='sales/schedule/%Y/%m/%d/')
    to_do = models.ForeignKey(ToDo, on_delete=models.CASCADE, related_name='attachments')
    name = models.CharField(blank=True, max_length=128, null=True)


class Messaging(BaseModel):
    class Meta:
        db_table = 'messaging'

    message = models.CharField(blank=True, max_length=128)
    to_do = models.ForeignKey(ToDo, on_delete=models.CASCADE, related_name='messaging')
    show_owner = models.BooleanField(blank=True, null=True)
    show_sub_vendors = models.BooleanField(blank=True, null=True)
    notify = models.ManyToManyField(get_user_model(), related_name='message_todo_notify',
                                    blank=True)


class DailyLog(BaseModel):
    class Meta:
        db_table = 'schedule_daily_log'
        ordering = ['-modified_date']

    title = models.CharField(blank=True, null=True, max_length=128)
    color = models.CharField(blank=True, null=True, max_length=128)
    date = models.DateTimeField()
    tags = models.ManyToManyField(TagSchedule, related_name='daily_log_tags')
    to_dos = models.ManyToManyField(ToDo, related_name='daily_log_to_dos')
    note = models.TextField(blank=True)
    lead_list = models.ForeignKey(LeadDetail, on_delete=models.CASCADE, related_name='daily_log_lead_list')
    internal_user_share = models.BooleanField(default=False)
    internal_user_notify = models.BooleanField(default=False)
    sub_member_share = models.BooleanField(default=False)
    sub_member_notify = models.BooleanField(default=False)
    owner_share = models.BooleanField(default=False)
    owner_notify = models.BooleanField(default=False)
    private_share = models.BooleanField(default=False)
    private_notify = models.BooleanField(default=False)
    to_do = models.ForeignKey(ToDo, on_delete=models.SET_NULL, related_name='daily_log_todo_id', null=True)
    event = models.ForeignKey('ScheduleEvent', on_delete=models.SET_NULL, related_name='daily_log_event', null=True)


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
    name = models.CharField(blank=True, max_length=128, null=True)


class CommentDailyLog(BaseModel):
    class Meta:
        db_table = 'daily_log_comment'
        ordering = ['-modified_date']

    daily_log = models.ForeignKey(DailyLog, on_delete=models.CASCADE, related_name='comment_daily_log')
    comment = models.TextField(blank=True)


class AttachmentCommentDailyLog(BaseModel):
    class Meta:
        db_table = 'attachment_comment_daily_log'
        ordering = ['-modified_date']

    comment = models.ForeignKey(CommentDailyLog, on_delete=models.CASCADE, related_name='attachment_daily_log_comment')
    file = models.FileField(upload_to='sales/schedule/%Y/%m/%d/')
    name = models.CharField(blank=True, max_length=128, null=True)


class ScheduleEventSetting(BaseModel):
    class Meta:
        db_table = 'schedule_event_setting'

    default_builder_view = models.CharField(max_length=128, choices=BuilderView.choices,
                                            default=BuilderView.CALENDAR_DAY)
    default_item_reminder = models.IntegerField(blank=True, null=True, choices=ReminderType.choices,
                                                default=ReminderType.NO)
    send_confirm = models.BooleanField(default=False)
    default_notify = models.BooleanField(default=False)
    show_time_for_hour = models.BooleanField(default=False)
    automatically_mark = models.BooleanField(default=False)
    default_show_subs_vendors = models.BooleanField(default=False)
    include_header = models.BooleanField(default=False)


class ScheduleEventPhaseSetting(BaseModel):
    class Meta:
        db_table = 'schedule_event_phase_setting'

    label = models.CharField(blank=True, max_length=128, null=True)
    display_order = models.IntegerField(blank=True, null=True)
    color = models.CharField(blank=True, max_length=128, null=True)
    event_setting = models.ForeignKey(Config, related_name='schedule_event_setting_phase',
                                      null=True, blank=True, on_delete=models.SET_NULL)


class ScheduleEvent(BaseModel):
    class Meta:
        db_table = 'schedule_event'

    lead_list = models.ForeignKey(LeadDetail, on_delete=models.CASCADE, related_name='schedule_event_lead_list')
    event_title = models.CharField(blank=True, max_length=128)
    assigned_user = models.ManyToManyField(get_user_model(), related_name='schedule_event_assigned_user',
                                           blank=True)
    reminder = models.IntegerField(blank=True, null=True, choices=ReminderType.choices, default=ReminderType.NO)
    start_day = models.DateTimeField(null=True, blank=True)
    end_day = models.DateTimeField(null=True, blank=True)
    start_hour = models.DateTimeField(blank=True, null=True)
    end_hour = models.DateTimeField(null=True, blank=True)
    due_days = models.IntegerField(default=None, null=True, blank=True)
    time = models.IntegerField(blank=True, null=True)
    is_before = models.BooleanField(default=False, blank=True)
    is_after = models.BooleanField(default=False, blank=True)
    viewing = models.ManyToManyField(get_user_model(), related_name='schedule_event_viewing',
                                     blank=True)
    color = models.CharField(blank=True, max_length=128, null=True)
    notes = models.TextField(blank=True, null=True)
    internal_notes = models.TextField(blank=True, null=True)
    sub_notes = models.TextField(blank=True, null=True)
    owner_notes = models.TextField(blank=True, null=True)
    is_root = models.BooleanField(default=False)
    type = models.CharField(max_length=128, choices=Type.choices, blank=True, null=True)
    lag_day = models.IntegerField(default=0, blank=True, null=True)
    predecessor = models.ForeignKey('self', related_name='parent_event', null=True,
                                    blank=True, on_delete=models.SET_NULL, default=None)
    link_to_outside_calendar = models.BooleanField(default=False, blank=True, null=True)
    tags = models.ManyToManyField(TagSchedule, related_name='event_tags', blank=True)
    phase_label = models.CharField(blank=True, max_length=128, null=True)
    phase_display_order = models.IntegerField(blank=True, null=True)
    phase_color = models.CharField(blank=True, max_length=128, null=True)
    phase_setting = models.ForeignKey(ScheduleEventPhaseSetting, blank=True, null=True,
                                      on_delete=models.SET_NULL, related_name='event_phase')
    todo = models.ForeignKey(ToDo, on_delete=models.SET_NULL, related_name='schedule_event_to_do', blank=True,
                             null=True)
    daily_log = models.ForeignKey(DailyLog, on_delete=models.SET_NULL, related_name='schedule_event_daily_log',
                                  blank=True, null=True)


class MessageEvent(BaseModel):
    class Meta:
        db_table = 'schedule_event_message'

    event = models.ForeignKey(ScheduleEvent, on_delete=models.CASCADE, related_name='event_message')
    message = models.TextField()
    show_owner = models.BooleanField(default=False, blank=True, null=True)
    show_sub_vendors = models.BooleanField(default=False, blank=True, null=True)
    notify = models.ManyToManyField(get_user_model(), related_name='message_vent_notify',
                                    blank=True)


class ShiftReason(BaseModel):
    class Meta:
        db_table = 'shift_reason'

    title = models.CharField(max_length=64)


class EventShiftReason(BaseModel):
    class Meta:
        db_table = 'event_shift_reason'

    shift_reason = models.ForeignKey(ShiftReason, on_delete=models.SET_NULL, related_name='event_shift', blank=True,
                                     null=True)
    shift_note = models.TextField(blank=True, null=True)
    # event_shift = models.ForeignKey('ScheduleEventShift', on_delete=models.CASCADE,
    #                                 related_name='schedule_event_shift_reason', blank=True, null=True)


class ScheduleEventShift(BaseModel):
    class Meta:
        db_table = 'schedule_event_shift'

    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, related_name='event_shift_history_user')
    start_day = models.DateTimeField(blank=True, null=True)
    start_day_after_change = models.DateTimeField(blank=True, null=True)
    end_day = models.DateTimeField(blank=True, null=True)
    end_day_after_change = models.DateTimeField(blank=True, null=True)
    source = models.CharField(blank=True, max_length=128, null=True)
    reason = models.ForeignKey(EventShiftReason, on_delete=models.SET_NULL, related_name='schedule_event_shift_reason',
                               blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    event = models.ForeignKey(ScheduleEvent, on_delete=models.CASCADE, related_name='shift_event')
    is_direct = models.BooleanField(blank=True, null=True)


class FileScheduleEvent(BaseModel):
    class Meta:
        db_table = 'schedule_event_file'

    file = models.FileField(upload_to='sales/schedule/%Y/%m/%d/')
    event = models.ForeignKey(ScheduleEvent, on_delete=models.CASCADE, related_name='event_file')
    name = models.CharField(blank=True, max_length=128, null=True)


class DataType(models.TextChoices):
    SINGLE_LINE_TEXT = 'single_line_text', 'Single line text'
    MULTI_LINE_TEXT = 'multi_line_text_with_expandable_textbox', 'Multi line text with expandable textbox'
    CHECKBOX = 'checkbox', 'Checkbox'
    WHOLE_NUMBER = 'whole_number', 'Whole_number'
    LIST_OF_USER_SINGLE_SELECT = 'list_of_user_single_select', 'List of user single select'
    LIST_OF_SUBS_VENDORS_SINGLE_SELECT = 'list_of_subs_vendors_single_select', 'List of subs vendors single select'
    DATE = 'date', 'Date'
    CURRENCY = 'currency', 'Currency'
    DROPDOWN = 'dropdown', 'Dropdown'
    FILE = 'file', 'File',
    MULTI_SELECT_DROPDOWN = 'multi_select_dropdown', 'Multi select dropdown'
    LINK = 'link', 'Link'
    LIST_OF_USER_MULTI_SELECT = 'list_of_user_multi_select', 'list of user multi select'
    LIST_OF_SUBS_VENDORS_MULTI_SELECT = 'list_of_subs_vendors_multi_select', 'list of subs vendors multi select'


class ScheduleDailyLogSetting(BaseModel):
    class Meta:
        db_table = 'schedule_daily_log_setting'

    stamp_location = models.BooleanField(default=False)
    default_notes = models.TextField(blank=True, null=True)
    internal_user_share = models.BooleanField(default=False)
    internal_user_notify = models.BooleanField(default=False)
    sub_member_share = models.BooleanField(default=False)
    sub_member_notify = models.BooleanField(default=False)
    owner_share = models.BooleanField(default=False)
    owner_notify = models.BooleanField(default=False)
    private_share = models.BooleanField(default=False)
    private_notify = models.BooleanField(default=False)
    user = models.OneToOneField(get_user_model(), related_name='user_setting_schedule_daily_log',
                                blank=True, on_delete=models.CASCADE, null=True)


class CustomFieldScheduleDailyLogSetting(BaseModel):
    class Meta:
        db_table = 'custom_field_schedule_daily_log_setting'
        ordering = ['display_order']

    label = models.CharField(blank=True, max_length=128)
    data_type = models.CharField(max_length=128, choices=DataType.choices, default=DataType.SINGLE_LINE_TEXT)
    required = models.BooleanField(default=False)
    include_in_filters = models.BooleanField(default=False)
    display_order = models.IntegerField(default=0, blank=True, null=True)
    tool_tip_text = models.CharField(blank=True, max_length=128, null=True)
    show_owners = models.BooleanField(default=False)
    allow_permitted_sub = models.BooleanField(default=False)
    default_value = models.CharField(blank=True, max_length=128)
    default_date = models.DateTimeField(null=True, blank=True)
    default_checkbox = models.BooleanField(null=True, blank=True)
    default_number = models.IntegerField(blank=True, null=True)
    daily_log_setting = models.ForeignKey(Config, related_name='custom_filed_daily_log_setting',
                                          null=True, blank=True, on_delete=models.SET_NULL)


class ScheduleToDoSetting(BaseModel):
    class Meta:
        db_table = 'schedule_todo_setting'

    reminder = models.IntegerField(blank=True, null=True, default=0)
    is_move_completed = models.BooleanField(default=False)


class CustomFieldScheduleSetting(BaseModel):
    class Meta:
        db_table = 'custom_field_schedule_todo_setting'
        ordering = ['display_order']

    label = models.CharField(blank=True, max_length=128)
    data_type = models.CharField(max_length=128, choices=DataType.choices, default=DataType.SINGLE_LINE_TEXT)
    required = models.BooleanField(default=False)
    include_in_filters = models.BooleanField(default=False)
    display_order = models.IntegerField(default=0, blank=True, null=True)
    tool_tip_text = models.CharField(blank=True, max_length=128, null=True)
    show_owners = models.BooleanField(default=False)
    allow_permitted_sub = models.BooleanField(default=False)
    default_value = models.CharField(blank=True, max_length=128)
    default_date = models.DateTimeField(null=True, blank=True)
    default_checkbox = models.BooleanField(null=True, blank=True)
    default_number = models.IntegerField(blank=True, null=True)
    todo_setting = models.ForeignKey(Config, related_name='custom_filed_to_do_setting',
                                     null=True, blank=True, on_delete=models.SET_NULL)


class ItemFieldDropDown(BaseModel):
    class Meta:
        db_table = 'item_dropdown'

    dropdown = models.ForeignKey(CustomFieldScheduleSetting, on_delete=models.CASCADE,
                                 related_name='custom_field_drop_down')
    name = models.CharField(blank=True, max_length=128)


class ItemFieldDropDownDailyLog(BaseModel):
    class Meta:
        db_table = 'item_dropdown_daily_log'

    dropdown = models.ForeignKey(CustomFieldScheduleDailyLogSetting, on_delete=models.CASCADE,
                                 related_name='custom_field_daily_log_drop_down')
    name = models.CharField(blank=True, max_length=128)


class TodoCustomField(BaseModel):
    class Meta:
        db_table = 'todo_custom_field'

    todo = models.ForeignKey(ToDo, related_name='custom_filed_to_do',
                             null=True, blank=True, on_delete=models.SET_NULL)
    label = models.CharField(blank=True, max_length=128)
    data_type = models.CharField(max_length=128, choices=DataType.choices, default=DataType.SINGLE_LINE_TEXT)
    required = models.BooleanField(default=False)
    include_in_filters = models.BooleanField(default=False)
    display_order = models.IntegerField(default=0, blank=True, null=True)
    tool_tip_text = models.CharField(blank=True, max_length=128, null=True)
    show_owners = models.BooleanField(default=False)
    allow_permitted_sub = models.BooleanField(default=False)
    value = models.CharField(blank=True, max_length=128, null=True)
    value_date = models.DateTimeField(null=True, blank=True)
    value_checkbox = models.BooleanField(default=False, null=True, blank=True)
    value_number = models.IntegerField(default=0, blank=True, null=True)
    custom_field = models.ForeignKey(CustomFieldScheduleSetting, related_name='custom_filed_setting',
                                     null=True, blank=True, on_delete=models.SET_NULL)


class DailyLogCustomField(BaseModel):
    class Meta:
        db_table = 'daily_log_custom_field'

    daily_log = models.ForeignKey(DailyLog, related_name='custom_filed_daily_log',
                                  null=True, blank=True, on_delete=models.SET_NULL)
    label = models.CharField(blank=True, max_length=128)
    data_type = models.CharField(max_length=128, choices=DataType.choices, default=DataType.SINGLE_LINE_TEXT)
    required = models.BooleanField(default=False)
    include_in_filters = models.BooleanField(default=False)
    display_order = models.IntegerField(default=0, blank=True, null=True)
    tool_tip_text = models.CharField(blank=True, max_length=128, null=True)
    show_owners = models.BooleanField(default=False)
    allow_permitted_sub = models.BooleanField(default=False)
    value = models.CharField(blank=True, max_length=128, null=True)
    value_date = models.DateTimeField(null=True, blank=True)
    value_checkbox = models.BooleanField(default=False, null=True, blank=True)
    value_number = models.IntegerField(default=0, blank=True, null=True)
    custom_field = models.ForeignKey(CustomFieldScheduleDailyLogSetting, related_name='custom_filed_setting_daily_log',
                                     null=True, blank=True, on_delete=models.SET_NULL)
