# ==============================================================================
# ARQUIVO: hotel_project/hotel_project/settings.py
# DESCRIÇÃO: Arquivo principal de configurações do projeto Django.
# ==============================================================================
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SECRET_KEY = 'django-insecure-chave-secreta-de-exemplo' # Em produção, use uma chave segura!

DEBUG = False 

ALLOWED_HOSTS = ["127.0.0.1", "localhost", 'laaztech.com'] # Em produção, coloque seu domínio aqui, ex: ['meuhotel.com']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    # Nosso app principal
    'gestao',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'pousada_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
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

WSGI_APPLICATION = 'pousada_project.wsgi.application'

# --- CONFIGURAÇÃO DO BANCO DE DADOS MYSQL ---
# Edite com as informações do seu XAMPP/servidor MySQL
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.mysql',
#         'NAME': 'hotel_db',      # Nome do banco de dados criado no phpMyAdmin
#         'USER': 'root',          # Usuário padrão do XAMPP
#         'PASSWORD': 'admin',          # Senha padrão do XAMPP (vazia)
#         'HOST': '127.0.0.1',
#         'PORT': '3307',
#         'OPTIONS': {
#             'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
#         },
#     }
# }
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    # validadores de senha...
]

LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
USE_L10N = True
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ==========================================================
# === CONFIGURAÇÕES DE AUTENTICAÇÃO E LOGIN              ===
# ==========================================================
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'dashboard' # A 'name' da URL do seu painel principal

# settings.py
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')