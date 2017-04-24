"""
Django settings for proaixy project.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.6/ref/settings/
"""

import djcelery
from datetime import timedelta

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
BASE_DIR = os.path.dirname(os.path.dirname(__file__))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.6/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '0nvws#b%zcj!@5xp271t%@w=3b72l0a0_qn*(axiu-4i2-je7_'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

TEMPLATE_DEBUG = True

ALLOWED_HOSTS = []


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'oai',
    'djcelery',
    'templatetag_handlebars',
]

MIDDLEWARE_CLASSES = [
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'proaixy.urls'

WSGI_APPLICATION = 'proaixy.wsgi.application'

# Logging

LOGGING = {
        'version': 1,
        'handlers': {
            'file': {
                'level': 'DEBUG',
                'class': 'logging.FileHandler',
                'filename': '/home/pintoch/proaixy/logs/django-debug.log',
                },
           },
        'loggers': {
            'django.request': {
                'handlers':['file'],
                'level':'DEBUG',
                'propagate': True,
                },
            },
        }

# Database
# https://docs.djangoproject.com/en/1.6/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'proaixy',
        'USER': 'dissemin',
        'PASSWORD': 'dissemin'
    }
}

<<<<<<< HEAD
=======
TEMPLATES = [{
    'BACKEND':'django.template.backends.django.DjangoTemplates',
    'OPTIONS': {
        'loaders': [
            'django.template.loaders.eggs.Loader',
            'django.template.loaders.app_directories.Loader',
        ],
        'context_processors': [
            'django.contrib.auth.context_processors.auth',
        ],
        }
    }]

CACHES = {
        'default': {
            # This one uses Redis, which is already required for message-passing
            # to Celery, so let's use it as a cache too
             'BACKEND': 'redis_cache.RedisCache',
             'LOCATION': ('localhost:6379'),
             'OPTIONS': {
                 'DB': 0,
             },
            }
}

CACHE_MACHINE_USE_REDIS = True
REDIS_BACKEND = 'redis://localhost:6379'

>>>>>>> eba7d88... Optimize OAI endpoint
# Login and athentication
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'

# Internationalization
# https://docs.djangoproject.com/en/1.6/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.6/howto/static-files/

STATIC_URL = '/static/'

# Celery config
djcelery.setup_loader()
BROKER_URL = 'amqp://guest:guest@127.0.0.1:5672//'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
# This has to be added to the model instead.

CELERYBEAT_SCHEDULE = {
    'cleanup_resumption_tokens': {
                'task': 'oai.tasks.cleanup_resumption_tokens',
                'schedule': timedelta(days=1),
                'args': ()},
    }
CELERYBEAT_SCHEDULER = 'djcelery.schedulers.DatabaseScheduler'

CELERY_TIMEZONE = 'UTC'

