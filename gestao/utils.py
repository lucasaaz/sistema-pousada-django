# gestao/utils.py
import boto3
from django.conf import settings
from botocore.exceptions import NoCredentialsError

def upload_file_to_s3(file, filename):
    """
    Envia o arquivo para o bucket S3 e retorna a URL pública.
    """
    s3 = boto3.client(
        's3',
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_S3_REGION_NAME
    )

    try:
        s3.upload_fileobj(
            Fileobj=file,
            Bucket=settings.AWS_STORAGE_BUCKET_NAME,
            Key=filename,
            ExtraArgs={'ACL': 'public-read'}  # deixa público
        )
        url = f"https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.{settings.AWS_S3_REGION_NAME}.amazonaws.com/{filename}"
        return url
    except NoCredentialsError:
        print("Credenciais inválidas")
        return None
