# gestao/utils.py
import boto3
import mimetypes
from django.conf import settings
from botocore.exceptions import NoCredentialsError, ClientError
from urllib.parse import quote


def upload_file_to_s3(fileobj, filename, acl='public-read', content_type=None):
    """
    Envia o arquivo para o bucket S3 e retorna a URL pública ou levanta exceção em falha.
    - fileobj: file-like (ex: InMemoryUploadedFile)
    - filename: chave no bucket (ex: 'clientes/123/foto.jpg')
    - acl: 'private' ou 'public-read'
    - content_type: MIME type (ex: 'image/jpeg'), opcional

    Observações/robustez:
    - Se content_type não for informado, tenta inferir via mimetypes a partir do filename.
    - Garante seek(0) antes do upload.
    - Retorna uma URL pública construída de forma segura (assincronia com regiões).
    """
    bucket = getattr(settings, 'AWS_STORAGE_BUCKET_NAME', None)
    region = getattr(settings, 'AWS_S3_REGION_NAME', None)

    if not bucket:
        raise RuntimeError("AWS_STORAGE_BUCKET_NAME não configurado em settings")

    s3 = boto3.client(
        's3',
        aws_access_key_id=getattr(settings, 'AWS_ACCESS_KEY_ID', None),
        aws_secret_access_key=getattr(settings, 'AWS_SECRET_ACCESS_KEY', None),
        region_name=region,
    )

    # garantir que o ponteiro do arquivo esteja no início
    try:
        fileobj.seek(0)
    except Exception:
        pass

    # tenta inferir content-type se não fornecido
    if not content_type:
        content_type, _ = mimetypes.guess_type(filename)

    extra_args = {}
    if content_type:
        extra_args['ContentType'] = content_type
    if acl:
        extra_args['ACL'] = acl

    try:
        s3.upload_fileobj(fileobj, bucket, filename, ExtraArgs=extra_args)
    except NoCredentialsError:
        raise RuntimeError("Credenciais AWS não encontradas/configuradas")
    except ClientError as e:
        raise RuntimeError(f"Erro ao enviar para S3: {e}")

    # monta URL pública de forma segura (escapa caracteres reservados no filename)
    quoted_filename = quote(filename)
    if region:
        url = f"https://{bucket}.s3.{region}.amazonaws.com/{quoted_filename}"
    else:
        url = f"https://{bucket}.s3.amazonaws.com/{quoted_filename}"
    return url
