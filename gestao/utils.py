import boto3
import os
from django.conf import settings
from botocore.exceptions import NoCredentialsError, ClientError

def upload_file_to_s3(file_obj, bucket_name, object_name):
    """
    Envia um arquivo para um bucket S3.
    Retorna a URL do arquivo se for bem-sucedido, None se falhar.
    """
    s3_client = boto3.client(
        's3',
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
        region_name=os.getenv('AWS_S3_REGION_NAME')
    )
    
    try:
        file_obj.seek(0)
        s3_client.upload_fileobj(
            file_obj,
            bucket_name,
            object_name,
            ExtraArgs={'ContentType': 'image/jpeg', 'ACL': 'public-read'}
        )
        
        # Constrói a URL
        region = os.getenv('AWS_S3_REGION_NAME')
        url = f"https://{bucket_name}.s3.{region}.amazonaws.com/{object_name}"
        return url

    except (NoCredentialsError, ClientError) as e:
        print(f"Erro no upload para o S3: {e}")
        return None