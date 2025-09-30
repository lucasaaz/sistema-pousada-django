# ==============================================================================
# ARQUIVO: hotel_project/hotel_project/settings.py
# DESCRIÇÃO: Arquivo principal de configurações do projeto Django.
# ==============================================================================
import os
import dj_database_url
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do ficheiro .env
load_dotenv() 

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Use variáveis de ambiente para a SECRET_KEY e o DEBUG
SECRET_KEY = os.environ.get('SECRET_KEY')
DEBUG = False

# ALLOWED_HOSTS pode ser configurado via variável de ambiente com valores separados por vírgula
ALLOWED_HOSTS = []

# Adiciona o host da Render quando estiver em produção
RENDER_EXTERNAL_HOSTNAME = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)


INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_select2',
    'django.contrib.humanize',
    'storages',
    # Nosso app principal
    'gestao',
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

# Configuração da Base de Dados (lê a URL fornecida pela Render)
DATABASES = {
    'default': dj_database_url.config(
        default=os.environ.get('DATABASE_URL'),
        conn_max_age=600
    )
}

AUTH_PASSWORD_VALIDATORS = [
    # validadores de senha...
]

LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
USE_L10N = True
USE_TZ = True

# ==========================================================
# === CONFIGURAÇÕES DE AUTENTICAÇÃO E LOGIN              ===
# ==========================================================
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'dashboard' # A 'name' da URL do seu painel principal

# settings.py (nota: STATIC_ROOT já definido acima)

# ==========================================================
# === CONFIGURAÇÕES DE ARQUIVOS ESTÁTICOS E MÍDIA        ===
# ==========================================================
STATIC_URL = '/static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Configuração do campo padrão para chaves primárias
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

if not DEBUG:
    # =======================
    # --- PRODUÇÃO (Render) -
    # =======================
    AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
    AWS_STORAGE_BUCKET_NAME = os.getenv('AWS_STORAGE_BUCKET_NAME')
    AWS_S3_REGION_NAME = os.getenv('AWS_S3_REGION_NAME', 'sa-east-1')

    # Domínio do bucket
    AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.s3.{AWS_S3_REGION_NAME}.amazonaws.com'

    AWS_S3_FILE_OVERWRITE = False
    AWS_DEFAULT_ACL = None
    AWS_S3_VERIFY = True

    # Arquivos estáticos → S3
    STATICFILES_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"
    STATIC_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/static/"

    # Arquivos de mídia → S3
    DEFAULT_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"
    MEDIA_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/media/"

else:
    # =======================
    # --- DESENVOLVIMENTO ---
    # =======================
    MEDIA_URL = '/media/'
    MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

    # WhiteNoise para servir estáticos localmente
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'