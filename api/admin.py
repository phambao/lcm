# Register your models here.
import random
import string

from django.template.loader import render_to_string
from django.contrib import admin, messages
from django.core.mail import send_mail
from django.conf import settings
from django.utils.timesince import timesince
from django.http import HttpResponseRedirect
from django.urls import reverse
from api.models import CompanyBuilder, User
from base.models.config import Question, Answer


class UserInline(admin.TabularInline):
    model = User
    extra = 0
    can_delete = False
    fields = ["username", "first_name", "last_name", "email", "is_active"]


class CompanyAdmin(admin.ModelAdmin):
    list_display = ["company_name", "logo", "business_phone", "size"]
    fields = ["company_name", "logo", "business_phone", "size"]
    list_filter = ["company_name"]
    search_fields = ['company_name', 'business_phone']
    inlines = [UserInline]

    def response_change(self, request, obj):
        if getattr(self, 'formset_saved', True):
            company_id = obj.pk
            change_url = reverse('admin:api_companybuilder_change', args=[company_id])
            return HttpResponseRedirect(change_url)

        return super().response_change(request, obj)

    def save_formset(self, request, form, formset, change):
        if formset.model == User:
            instances = formset.save(commit=False)
            for instance in instances:
                if instance.pk is None:
                    new_password = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
                    instance.set_password(new_password)
                    instance.save()
                    subject = f'Reset Password for {instance.get_username()}'
                    content = render_to_string('auth/create-user.html', {'username': instance.get_username(),
                                                                         'password': new_password})
                    send_mail(subject, content, settings.EMAIL_HOST_USER, [instance.email])
                else:
                    instance.save()
            formset.save_m2m()
            formset_saved = True

        else:
            super().save_formset(request, form, formset, change)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs = qs.prefetch_related('user_company_builder')
        return qs

    def user_count(self, obj):
        return obj.user_set.count()

    user_count.short_description = "User Count"


class UserAdmin(admin.ModelAdmin):
    list_display = ["username", "first_name", "last_name", "email", "company", "is_active",
                    "display_last_login"]
    list_filter = ["company"]
    exclude = ['password']
    actions = ['enable_users', 'disable_users', "reset_password"]
    search_fields = ['username', 'first_name', 'last_name', 'email', 'company__company_name']

    def save_model(self, request, obj, form, change):
        if obj.id is None:
            new_password = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
            obj.set_password(new_password)
            obj.save()
            subject = f'Reset Password for {obj.get_username()}'
            content = render_to_string('auth/create-user.html', {'username': obj.get_username(),
                                                                 'password': new_password})
            send_mail(subject, content, settings.EMAIL_HOST_USER, [obj.email])

        obj.save()

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs

    def enable_users(self, request, queryset):
        queryset.update(is_active=True)

    def disable_users(self, request, queryset):
        queryset.update(is_active=False)

    def reset_password(self, request, queryset):
        for user in queryset:
            try:
                new_password = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
                user.set_password(new_password)
                user.save()
                subject = f'Reset Password for {user.get_username()}'
                content = render_to_string('auth/reset-password.html', {'username': user.get_username(),
                                                                        'new_password': new_password})
                send_mail(subject, content, settings.EMAIL_HOST_USER, [user.email])
            except Exception as e:
                messages.error(request, 'Email invalid')

    reset_password.short_description = "Reset Password"

    def display_last_login(self, obj):
        if obj.last_login:
            timesince_str = timesince(obj.last_login)
            first_value = timesince_str.split(",")[0].strip()
            return first_value
        return None

    display_last_login.short_description = "Last Login"


class QuestionAdmin(admin.ModelAdmin):
    list_display = ('id', 'type', 'name')
    search_fields = ['name']


class AnswerAdmin(admin.ModelAdmin):
    list_display = ('id', 'question', 'name')
    search_fields = ['name', 'question']


admin.site.register(User, UserAdmin)
admin.site.register(CompanyBuilder, CompanyAdmin)
admin.site.register(Question, QuestionAdmin)
admin.site.register(Answer, AnswerAdmin)
