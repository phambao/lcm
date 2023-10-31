"""
Django settings for lcm project.

Generated by 'django-admin startproject' using Django 3.2.13.

For more information on this file, see
https://docs.djangoproject.com/en/3.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/3.2/ref/settings/
"""

from pathlib import Path

from decouple import config
import os
# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent
BASE_URL = config('BASE_URL', None)
LOCALE_PATHS = [
    os.path.join(BASE_DIR, 'locale'),
]

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-+!6)qy$jksu(=9q0shugfted1&yqvu%dl7-yb74cgdunb55u41'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('ENVIRONMENT') == 'development'

ALLOWED_HOSTS = ['*']


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    "corsheaders",
    'rest_framework_simplejwt',
    'knox', # Need to remove
    'drf_yasg',
    'django_filters',
    'base.apps.BaseConfig',
    'api.apps.ApiConfig',
    'sales.apps.SalesConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'api.middleware.CacheRequestMiddleware',
    'api.middleware.SettingTranslateMiddleware'
]

AUTHENTICATION_BACKENDS = [
    'api.backend.EmailBackend',
    'django.contrib.auth.backends.ModelBackend'
]

ROOT_URLCONF = 'lcm.urls'
# SPECTACULAR_SETTINGS = {
#     'TITLE': 'Student API',
#     'DESCRIPTION': 'This is a student official API documentation.',
#     'VERSION': '1.0.0',
#     'SERVE_INCLUDE_SCHEMA': False
# }
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'lcm.wsgi.application'


# Database
# https://docs.djangoproject.com/en/3.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': config('DB_ENGINE'),
        'HOST': config('DB_HOST'),
        'PORT': config('DB_PORT'),
        'NAME': config('DB_NAME'),
        'PASSWORD': config('DB_PASSWORD'),
        'USER': config('DB_USER')
    }
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
        'LOCATION': 'lcm_cache_table',
    }
}

# Password validation
# https://docs.djangoproject.com/en/3.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

AUTH_USER_MODEL = 'api.User'

USE_CLOUD_STORAGE = config('USE_CLOUD_STORAGE', default=False, cast=bool)

DEFAULT_RENDERER_CLASSES = [
    'rest_framework.renderers.JSONRenderer',
]

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES':
        (
         'rest_framework.authentication.SessionAuthentication',
         'rest_framework_simplejwt.authentication.JWTAuthentication',
         ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.LimitOffsetPagination',
    'PAGE_SIZE': 25,
    'DEFAULT_FILTER_BACKENDS': ['django_filters.rest_framework.DjangoFilterBackend'],
    'DEFAULT_METADATA_CLASS': 'base.metadata.SimpleMetadata',
    'DEFAULT_RENDERER_CLASSES': DEFAULT_RENDERER_CLASSES,
    'UPLOADED_FILES_USE_URL': True,
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.UserRateThrottle'
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/min',
        'user': '1000/min'
    }
    # 'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema'
}

# Build for local development
CORS_ALLOW_ALL_ORIGINS = config('CORS_ALLOW_ALL_ORIGINS', cast=bool, default=False)

# Internationalization
# https://docs.djangoproject.com/en/3.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True

STATIC_ROOT = '/static'

if USE_CLOUD_STORAGE:
    DEFAULT_FILE_STORAGE = config('DEFAULT_FILE_STORAGE', default='django.core.files.storage.FileSystemStorage')
    STATICFILES_STORAGE = config('STATICFILES_STORAGE', default='django.contrib.staticfiles.storage.StaticFilesStorage')
    AWS_S3_REGION_NAME = config('AWS_S3_REGION_NAME', default='')
    AWS_S3_ENDPOINT_URL = config('AWS_S3_ENDPOINT_URL', default='')
    AWS_ACCESS_KEY_ID = config('AWS_ACCESS_KEY_ID', default='')
    AWS_SECRET_ACCESS_KEY = config('AWS_SECRET_ACCESS_KEY', default='')
    AWS_STORAGE_BUCKET_NAME = config('AWS_STORAGE_BUCKET_NAME', default='')
    AWS_DEFAULT_ACL = 'public-read'
    AWS_QUERYSTRING_AUTH = False

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.2/howto/static-files/

STATIC_URL = '/static/'

# Default primary key field type
# https://docs.djangoproject.com/en/3.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
MEDIA_ROOT = "uploads/"
MEDIA_URL = '/media/'

# Email settings
EMAIL_BACKEND = config('EMAIL_BACKEND', default='django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = config('EMAIL_HOST', default='localhost')
EMAIL_PORT = config('EMAIL_PORT', default=25)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
EMAIL_USE_TLS = config('EMAIL_USE_TLS', cast=bool, default=False)
EMAIL_USE_SSL = config('EMAIL_USE_SSL', cast=bool, default=False)

REDIS_HOST = config('REDIS_HOST', default='localhost')
REDIS_PORT = config('REDIS_PORT', default='6379')
REDIS_CELERY_DATABASE = config('REDIS_CELERY_DATABASE', default='0')

USE_DEBUG_TOOLBAR = config('USE_DEBUG_TOOLBAR', cast=bool, default=False)

if DEBUG:

    DEFAULT_RENDERER_CLASSES.append(
        'rest_framework.renderers.BrowsableAPIRenderer',
    )

def show_toolbar(request):
    if USE_DEBUG_TOOLBAR:
        return True
    return False

DEBUG_TOOLBAR_CONFIG = {
    'SHOW_TOOLBAR_CALLBACK': show_toolbar,
}

if USE_DEBUG_TOOLBAR:

    INSTALLED_APPS.append('debug_toolbar')
    MIDDLEWARE.insert(2, "debug_toolbar.middleware.DebugToolbarMiddleware")
    import socket  # only if you haven't already imported this
    hostname, _, ips = socket.gethostbyname_ex(socket.gethostname())
    INTERNAL_IPS = [ip[: ip.rfind(".")] + ".1" for ip in ips] + ["127.0.0.1", "10.0.2.2"]
