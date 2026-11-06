"""
Django settings for reposleuth project.

Configured for local development and production deployment on Render.
"""

import os
from pathlib import Path
import dj_database_url
from dotenv import load_dotenv

# Load optional .env file for local development
load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Security settings
SECRET_KEY = os.environ.get(
    'SECRET_KEY',
    'django-insecure-@xfd7m$(cq0mzla*ze41xsa@zfka_1$6qj3fi(&4pwq9ie52g9'
)

# DEBUG defaults to True for local development, should be explicitly set to False in production
DEBUG = os.environ.get('DEBUG', 'True').lower() in ('true', '1', 't')

# Host configuration
ALLOWED_HOSTS = ['*'] if DEBUG else ['localhost', '127.0.0.1']
if 'ALLOWED_HOSTS' in os.environ:
    ALLOWED_HOSTS = [h.strip() for h in os.environ['ALLOWED_HOSTS'].split(',') if h.strip()]

# Render automatically provides RENDER_EXTERNAL_HOSTNAME
render_hostname = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
if render_hostname and render_hostname not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(render_hostname)

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'whitenoise.runserver_nostatic',
    'django.contrib.staticfiles',
    'analyzer',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'reposleuth.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'reposleuth.wsgi.application'

# Database configuration:
# Uses PostgreSQL on Render via DATABASE_URL if available;
# otherwise falls back to SQLite for seamless local development.
database_url = os.environ.get('DATABASE_URL')
if database_url:
    DATABASES = {
        'default': dj_database_url.config(
            default=database_url,
            conn_max_age=600,
            ssl_require=True
        )
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# Password validation
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

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]
STATIC_ROOT = BASE_DIR / 'staticfiles'

# WhiteNoise storage for compressed and fingerprinted static assets
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}

# Media files (for uploaded projects and extracted codebases)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Max upload size (50MB)
DATA_UPLOAD_MAX_MEMORY_SIZE = 52428800
FILE_UPLOAD_MAX_MEMORY_SIZE = 52428800

# CSRF Trusted Origins for Render
CSRF_TRUSTED_ORIGINS = ['https://*.onrender.com']
if render_hostname:
    CSRF_TRUSTED_ORIGINS.append(f"https://{render_hostname}")
if 'CSRF_TRUSTED_ORIGINS' in os.environ:
    for origin in os.environ['CSRF_TRUSTED_ORIGINS'].split(','):
        if origin.strip():
            CSRF_TRUSTED_ORIGINS.append(origin.strip())

# Production security settings
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = os.environ.get('SECURE_SSL_REDIRECT', 'True').lower() in ('true', '1', 't')
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    hsts_seconds = os.environ.get('SECURE_HSTS_SECONDS')
    if hsts_seconds:
        SECURE_HSTS_SECONDS = int(hsts_seconds)
        SECURE_HSTS_INCLUDE_SUBDOMAINS = True
        SECURE_HSTS_PRELOAD = True

