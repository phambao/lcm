from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.contrib.postgres.fields import ArrayField

from api.models import BaseModel, CompanyBuilder


class Column(models.Model):
    name = models.CharField(max_length=128, default="")
    params = ArrayField(models.CharField(max_length=64), blank=True)
    hidden_params = ArrayField(models.CharField(max_length=64), default=list, blank=True)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, null=True, blank=True)
    is_public = models.BooleanField(default=False, blank=True)
    is_active = models.BooleanField(default=False, blank=True)


class Search(BaseModel):
    name = models.CharField(max_length=64)
    params = models.CharField(max_length=512, blank=True)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, null=True, blank=True)

    class Meta:
        unique_together = ('name', 'company', 'content_type')


class Config(models.Model):
    settings = models.JSONField(default=dict)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, null=True, blank=True)

    class Meta:
        unique_together = ('user', 'content_type')


class GridSetting(models.Model):
    name = models.CharField(max_length=128)
    params = ArrayField(models.CharField(max_length=64), blank=True)
    hidden_params = ArrayField(models.CharField(max_length=64), default=list, blank=True)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, null=True, blank=True)
    is_public = models.BooleanField(default=False, blank=True)


class FileBuilder365(BaseModel):
    class Meta:
        db_table = 'file_builder365'

    file = models.FileField(upload_to='%Y/%m/%d/')
    name = models.CharField(blank=True, max_length=128)


class Type(models.TextChoices):
    TEXT = 'text', 'TEXT'
    CHOICE = 'choice', 'CHOICE'
    MULTIPLE_CHOICE = 'multiple', 'MULTIPLE_CHOICE'


class Question(models.Model):
    class Meta:
        db_table = 'question'

    type = models.CharField(max_length=128, choices=Type.choices, default=Type.CHOICE, blank=True)
    name = models.TextField(blank=True, null=True, default='')


class Answer(models.Model):
    class Meta:
        db_table = 'answer'

    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='question_answer', null=True)
    name = models.TextField(blank=True, null=True, default='')


class CompanyAnswerQuestion(models.Model):
    class Meta:
        db_table = 'company_answer_question'

    company = models.ForeignKey(CompanyBuilder, on_delete=models.CASCADE,
                                related_name='%(class)s_company_builder', null=True, blank=True)
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='question_company')
    answer = models.ManyToManyField(Answer, related_name='answer_company', blank=True)