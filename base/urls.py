from django.urls import path, include
from django.views.decorators.csrf import csrf_exempt
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions

from base.views import country_state_city, base, auth
from base.views.auth import PersonalInformationView, PersonalInformationDetailView
from base.views.base import update_language_user, QuestionGenericView, QuestionDetailGenericView, AnswerGenericView, \
    AnswerDetailGenericView, CompanyAnswerQuestionSerializerGenericView, \
    CompanyAnswerQuestionSerializerDetailGenericView, create_question_answer_company, update_question_answer_company, \
    get_data_config, manage_sub, manage_sub_detail, get_data_storage
# Define path for Base App ------------------------------------------------------
from base.views.country_state_city import address_search, detail_location
from base.views.payment import ProductPreviewDetail, ProductPreview, CreateCheckOutSession, \
    stripe_cancel_subscription, get_config, create_customer, create_subscription, cancel_subscription, \
    list_subscriptions, preview_invoice, update_subscription, webhook_received, PaymentHistoryStripePreview, \
    preview_subscription, check_promotion_code, update_customer, get_payment_history

url_base = [
    path('location/',
         include([
             path('countries/', country_state_city.CountryList.as_view()),
             path('mcountries/', country_state_city.CountryV2List.as_view()),
             path('countries/<int:pk_country>/states/',
                  country_state_city.CountryStateList.as_view()),
             path('countries/<int:pk_country>/states/<int:pk_state>/cities/',
                  country_state_city.CountryStateCityList.as_view()),
             path('zipcodes/', country_state_city.Zipcode.as_view()),
         ])
         ),
    path('location-google/', address_search),
    path('location-google-detail/<str:place_id>/', detail_location),
    path('content-type/', base.ContentTypeList.as_view()),
    path('search/', base.SearchLeadGenericView.as_view()),
    path('search/<int:pk>/', base.SearchLeadDetailGenericView.as_view()),
    path('column/', base.ColumnLeadGenericView.as_view()),
    path('column/<int:pk>/', base.ColumnLeadDetailGenericView.as_view()),
    path('column/<int:pk>/active/', base.active_column),
    path('grid-setting/', base.GridSettingListView.as_view()),
    path('grid-setting/<int:pk>/', base.GridSettingDetailGenericView.as_view()),
    path('config/<str:model>/', base.config_view),
    path('logs/', base.ActivityLogList.as_view()),
    path('logs/<int:pk>/', base.ActivityLogDetail.as_view()),
    path('company/', base.CompanyListView.as_view()),
    path('company/<int:pk>/', base.CompanyDetailGenericView.as_view()),
    path('company/division/', base.DivisionListView.as_view()),
    path('company/division/<int:pk>/', base.DivisionDetailGenericView.as_view()),
    path('delete/<int:content_type>/', base.delete_models),
    path('group/', auth.GroupList.as_view()),
    path('group/<int:pk>/', auth.GroupDetail.as_view()),
    path('permission/', auth.PermissionList.as_view()),
    path('permission/<int:pk>/', auth.PermissionDetail.as_view()),
    path('roles/', auth.get_permission),
    path('lang/<str:lang>/', update_language_user),
    path('product/<int:pk>/', ProductPreviewDetail.as_view()),
    path('product/', ProductPreview.as_view()),
    path('payment/stripe/create-checkout-session/', csrf_exempt(CreateCheckOutSession.as_view()), name='checkout_session'),
    path('payment/stripe/stripe-cancel-subscription/', stripe_cancel_subscription),
    path('payment/stripe/config/', get_config),
    path('payment/stripe/create-customer/', create_customer),
    path('payment/stripe/update-customer/<str:customer_id>/', update_customer),
    path('payment/stripe/create-subscription/', create_subscription),
    path('payment/stripe/check-promotion-code/', check_promotion_code),
    path('payment/stripe/cancel-subscription/', cancel_subscription),
    path('payment/stripe/subscriptions/', list_subscriptions),
    path('payment/stripe/subscription/<str:subscription_id>/', preview_subscription),
    path('payment/stripe/invoice-preview/', preview_invoice),
    path('payment/stripe/update-subscription/', update_subscription),
    path('payment/stripe/webhook/', webhook_received),
    path('payment/history/', PaymentHistoryStripePreview.as_view()),
    path('question/', QuestionGenericView.as_view()),
    path('question/<int:pk>/', QuestionDetailGenericView.as_view()),
    path('answer/', AnswerGenericView.as_view()),
    path('answer/<int:pk>/', AnswerDetailGenericView.as_view()),
    path('company/question/', CompanyAnswerQuestionSerializerGenericView.as_view()),
    path('company/question/<int:pk>/', CompanyAnswerQuestionSerializerDetailGenericView.as_view()),
    path('company/create-question/', create_question_answer_company),
    path('company/update-question/<int:company_id>/', update_question_answer_company),
    path('personal-information/<int:pk>/', PersonalInformationDetailView.as_view()),
    path('personal-information/', PersonalInformationView.as_view()),
    path('get-config/', get_data_config),
    path('company/setting/payment/manage/', manage_sub),
    path('company/setting/payment/manage/<str:subscription_id>/', manage_sub_detail),
    path('company/setting/payment/storage/<str:subscription_id>/', get_data_storage),
    path('company/setting/payment/history/', get_payment_history),

]
# Create schema view for Swagger ------------------------------------------------
schema_view_base = get_schema_view(
    openapi.Info(
        title='API FOR BASE APP',
        default_version='v1',
    ),
    patterns=[
        path('api/base/', include(url_base))
    ],
    public=True,
    permission_classes=[permissions.AllowAny],
)

urlpatterns = [
    path('', include(url_base)),
    path('', schema_view_base.with_ui(
        'swagger', cache_timeout=0), name='schema-swagger-ui'),
]
