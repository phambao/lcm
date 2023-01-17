from django.contrib.auth import get_user_model
from django.db import models

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

    date = models.DateTimeField()
    tags = models.ManyToManyField(TagSchedule, related_name='daily_log_tags', null=True)
    to_do = models.ManyToManyField(ToDo, related_name='daily_log_tags', null=True)
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
    event_setting = models.ForeignKey(ScheduleEventSetting, related_name='schedule_event_setting_phase',
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


# class ScheduleEventShiftHistory(BaseModel):
#     class Meta:
#         db_table = 'schedule_event_phase'
#
#     user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, related_name='event_shift_history_user')
#     start_day = models.DateTimeField(blank=True, null=True)
#     start_day_after_change = models.DateTimeField(blank=True, null=True)
#     end_day = models.DateTimeField(blank=True, null=True)
#     end_day_after_change = models.DateTimeField(blank=True, null=True)
#     slip = models.IntegerField(blank=True, null=True)
class FileScheduleEvent(BaseModel):
    class Meta:
        db_table = 'schedule_event_file'

    file = models.FileField(upload_to='sales/schedule/%Y/%m/%d/')
    event = models.ForeignKey(ScheduleEvent, on_delete=models.CASCADE, related_name='event_file')


class DataType(models.TextChoices):
    SINGLE_LINE_TEXT = 'single-line-text', 'SINGLE-LINE-TEXT'
    MULTI_LINE_TEXT = 'multi-line text with expandable textbox', 'MULTI-LINE TEXT WITH EXPANDABLE TEXTBOX'
    CHECKBOX = 'checkbox', 'CHECKBOX'
    WHOLE_NUMBER = 'whole number', 'WHOLE NUMBER'
    LIST_OF_USER_SINGLE_SELECT = 'list of User - Single Select', 'LIST OF USER - SINGLE SELECT'
    LIST_OF_SUBS_VENDORS_SINGLE_SELECT = 'List of Subs/Vendors - Single Select', 'LIST OF SUBS/VENDORS-SINGLE SELECT'
    DATE = 'date', 'DATE'
    CURRENCY = 'currency', 'CURRENCY'
    DROPDOWN = 'dropdown', 'DROPDOWN'
    FILE = 'file', 'FILE',
    MULTI_SELECT_DROPDOWN = 'Multi-Select-Dropdown', 'MULTI-SELECT-DROPDOWN'
    LINK = 'link', 'LINK'
    LIST_OF_USER_MULTI_SELECT = 'list of User - Multi Select', 'LIST OF USER - MULTI SELECT'
    LIST_OF_SUBS_VENDORS_MULTI_SELECT = 'List of Subs/Vendors - Multi Select', 'LIST OF SUBS/VENDORS-MULTI SELECT'


class ScheduleDailyLogSetting(BaseModel):
    class Meta:
        db_table = 'schedule_daily_log_setting'

    stamp_location = models.BooleanField(default=False)
    default_notes = models.TextField(blank=True, null=True)
    internal_user_is_share = models.BooleanField(default=False)
    internal_user_is_notify = models.BooleanField(default=False)
    subs_vendors_is_share = models.BooleanField(default=False)
    subs_vendors_is_notify = models.BooleanField(default=False)
    owner_is_share = models.BooleanField(default=False)
    owner_is_notify = models.BooleanField(default=False)


class CustomFieldScheduleDailyLogSetting(BaseModel):
    class Meta:
        db_table = 'custom_field_schedule_daily_log'

    label = models.CharField(blank=True, max_length=128)
    data_type = models.CharField(max_length=128, choices=DataType.choices, default=DataType.SINGLE_LINE_TEXT)
    required = models.BooleanField(default=False)
    include_in_filters = models.BooleanField(default=False)
    display_order = models.IntegerField(default=0, blank=True, null=True)
    tool_tip_text = models.CharField(blank=True, max_length=128, null=True)
    show_owners = models.BooleanField(default=False)
    allow_permitted_sub = models.BooleanField(default=False)
    default_value = models.CharField(blank=True, max_length=128)
    default_date = models.DateField(null=True, blank=True)
    default_checkbox = models.BooleanField(null=True, blank=True)
    default_number = models.IntegerField(blank=True, null=True)
    daily_log_setting = models.ForeignKey(ScheduleDailyLogSetting, related_name='custom_filed_daily_log_setting',
                                          null=True, blank=True, on_delete=models.SET_NULL)


class ScheduleToDoSetting(BaseModel):
    class Meta:
        db_table = 'schedule_todo_setting'

    reminder = models.IntegerField(blank=True, null=True, default=0)
    is_move_completed = models.BooleanField(default=False)


class CustomFieldScheduleSetting(BaseModel):
    class Meta:
        db_table = 'custom_field_schedule_setting'

    label = models.CharField(blank=True, max_length=128)
    data_type = models.CharField(max_length=128, choices=DataType.choices, default=DataType.SINGLE_LINE_TEXT)
    required = models.BooleanField(default=False)
    include_in_filters = models.BooleanField(default=False)
    display_order = models.IntegerField(default=0, blank=True, null=True)
    tool_tip_text = models.CharField(blank=True, max_length=128, null=True)
    show_owners = models.BooleanField(default=False)
    allow_permitted_sub = models.BooleanField(default=False)
    default_value = models.CharField(blank=True, max_length=128)
    default_date = models.DateField(null=True, blank=True)
    default_checkbox = models.BooleanField(null=True, blank=True)
    default_number = models.IntegerField(blank=True, null=True)
    todo_setting = models.ForeignKey(ScheduleToDoSetting, related_name='custom_filed_to_do_setting',
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
    value_date = models.DateField(null=True, blank=True)
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
    value_date = models.DateField(null=True, blank=True)
    value_checkbox = models.BooleanField(default=False, null=True, blank=True)
    value_number = models.IntegerField(default=0, blank=True, null=True)
    custom_field = models.ForeignKey(CustomFieldScheduleDailyLogSetting, related_name='custom_filed_setting_daily_log',
                                     null=True, blank=True, on_delete=models.SET_NULL)
