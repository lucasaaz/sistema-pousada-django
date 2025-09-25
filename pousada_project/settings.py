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
DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'

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
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
#     }
# }
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

STATIC_URL = '/static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]
# Pasta destino para collectstatic
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
# Usar WhiteNoise para servir arquivos estáticos em produção
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ==========================================================
# === CONFIGURAÇÕES DE AUTENTICAÇÃO E LOGIN              ===
# ==========================================================
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'dashboard' # A 'name' da URL do seu painel principal

# settings.py (nota: STATIC_ROOT já definido acima)

# --- CONFIGURAÇÃO DO ARMAZENAMENTO S3 ---
# Esta configuração só será ativada se DEBUG for False (ou seja, em produção na Render)
if not DEBUG:
    # Chaves da AWS (lidas das variáveis de ambiente da Render)
    AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
    AWS_STORAGE_BUCKET_NAME = os.getenv('AWS_STORAGE_BUCKET_NAME')
    AWS_S3_REGION_NAME = os.getenv('AWS_S3_REGION_NAME', 'sa-east-1') # Default para São Paulo
    
    # Configurações para o comportamento dos arquivos
    AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com'
    AWS_S3_FILE_OVERWRITE = False # Não sobrescreve arquivos com o mesmo nome
    AWS_DEFAULT_ACL = None # Usa as permissões do bucket por padrão
    AWS_S3_VERIFY = True # Verifica certificados SSL

    # AVISO PARA O DJANGO USAR O S3 PARA ARQUIVOS ESTÁTICOS
    STATICFILES_STORAGE = 'storages.backends.s3boto3.S3StaticStorage'
    
    # AVISO PARA O DJANGO USAR O S3 PARA ARQUIVOS DE MÍDIA (FOTOS DOS CLIENTES)
    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'

    # Define as URLs para os arquivos
    STATIC_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/static/'
    MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/media/'

# Se estiver em desenvolvimento (DEBUG=True), mantenha a configuração local
else:
    MEDIA_URL = '/media/'
    MEDIA_ROOT = os.path.join(BASE_DIR, 'media')