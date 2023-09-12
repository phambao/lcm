import re

from django.db import IntegrityError
from rest_framework import serializers

from api.middleware import get_request
from api.models import DivisionCompany, CompanyBuilder
from ..models.config import Column, Search, Config, GridSetting, Question, Answer, CompanyAnswerQuestion, \
    PersonalInformation
from ..utils import pop

from base.serializers import base


class ColumnSerializer(serializers.ModelSerializer):
    model = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = Column
        fields = ('id', 'name', 'params', 'content_type', 'user', 'model', 'is_public',
                  'hidden_params', 'is_active')
        extra_kwargs = {'is_active': {'read_only': True}}


class SearchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Search
        fields = ('id', 'name', 'params', 'content_type', 'user')

    def create(self, validated_data):
        try:
            return super().create(validated_data)
        except IntegrityError:
            raise serializers.ValidationError({'name': ['Name has been exists']})

    def update(self, instance, validated_data):
        try:
            return super().update(instance, validated_data)
        except IntegrityError:
            raise serializers.ValidationError({'name': ['Name has been exists']})


class CustomColumnSerializer(serializers.Serializer):
    id = serializers.IntegerField(allow_null=True)
    params = serializers.ListField(allow_null=True)


class CustomSearchSerializer(serializers.Serializer):
    id = serializers.IntegerField(allow_null=True)
    params = serializers.CharField(allow_null=True, allow_blank=True)


class ConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = Config
        fields = ('id', 'settings', 'content_type')


class GridSettingSerializer(serializers.ModelSerializer):
    model = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = GridSetting
        fields = ('id', 'name', 'params', 'content_type', 'user', 'model', 'is_public', 'hidden_params')


class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanyBuilder
        fields = ('id', 'logo', 'company_name', 'address', 'country', 'city', 'state', 'zip_code', 'tax', 'size',
                  'business_phone', 'fax', 'email', 'cell_phone', 'cell_mail', 'created_date', 'modified_date',
                  'user_create', 'user_update', 'currency', 'description', 'company_timezone', 'field', 'short_name')

    def validate(self, validated_data):
        short_name = validated_data['short_name']
        request = self.context.get('request')
        if CompanyBuilder.objects.filter(short_name=short_name).exists() and request.method == 'POST':
            raise serializers.ValidationError({"short_name": "This short_name already exists."})
        return validated_data


class DivisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = DivisionCompany
        fields = '__all__'


class QuestionSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)

    class Meta:
        model = Question
        fields = ('id', 'name', 'type')

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['answer'] = AnswerSerializer(instance.question_answer.all(), many=True).data
        return data


class AnswerSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)

    class Meta:
        model = Answer
        fields = ('id', 'question', 'name')


class QuestionAnswerInfoSerializer(serializers.Serializer):
    question = serializers.IntegerField(required=False)
    answer = AnswerSerializer(allow_null=True, required=False, many=True)


class CompanyAnswerQuestionSerializer(serializers.ModelSerializer):
    info = QuestionAnswerInfoSerializer(allow_null=True, required=False, many=True)

    class Meta:
        model = CompanyAnswerQuestion
        fields = ('company', 'info')


class CompanyAnswerQuestionResSerializer(serializers.ModelSerializer):

    class Meta:
        model = CompanyAnswerQuestion
        fields = '__all__'

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['question'] = Question.objects.filter(id=data['question']).values()
        data['answer'] = Answer.objects.filter(id__in=data['answer']).values()
        return data


class PersonalInformationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PersonalInformation
        fields = ('id', 'fullname', 'phone_number', 'email', 'position', 'address', 'company', 'first_name', 'last_name', 'nick_name')