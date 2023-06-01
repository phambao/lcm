# Register your models here.
import random
import string

from django.template.loader import render_to_string
from django.contrib import admin, messages
from django.core.mail import send_mail
from django.conf import settings
from django.utils.timesince import timesince
from django.db import models

from api.models import CompanyBuilder, User


class CompanyAdmin(admin.ModelAdmin):
    list_display = ["company_name", "logo", "business_phone", "size"]
    fields = ["company_name", "logo", "business_phone", "size"]
    list_filter = ["company_name"]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs = qs.prefetch_related('user_company_builder')
        return qs

    def user_count(self, obj):
        return obj.user_set.count()

    user_count.short_description = "User Count"

    def get_inline_instances(self, request, obj=None):
        # Thêm inline của User vào trang chi tiết CompanyBuilder
        inline_instances = super().get_inline_instances(request, obj)
        if obj:
            inline_instances.append(UserInline(self.model, self.admin_site))
        return inline_instances


class UserAdmin(admin.ModelAdmin):
    list_display = ["username", "password", "first_name", "last_name", "email", "company", "is_active",
                    "display_last_login"]
    list_filter = ["company"]
    actions = ['enable_users', 'disable_users', "reset_password"]

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


class UserInline(admin.TabularInline):
    model = User
    extra = 0
    fields = ["username", "password", "first_name", "last_name", "email", "is_active"]
    readonly_fields = ["username", "password", "first_name", "last_name", "email", "is_active"]


admin.site.register(User, UserAdmin)
admin.site.register(CompanyBuilder, CompanyAdmin)
