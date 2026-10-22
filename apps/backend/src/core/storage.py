import boto3
from src.core.config import MINIO_ENDPOINT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY, MINIO_BUCKET, CLIP_RETENTION_DAYS

s3_client = boto3.client(
    's3',
    endpoint_url=MINIO_ENDPOINT,
    aws_access_key_id=MINIO_ACCESS_KEY,
    aws_secret_access_key=MINIO_SECRET_KEY
)

def generate_presigned_download_url(object_name: str, expires_in: int = 3600) -> str:
    return s3_client.generate_presigned_url(
        'get_object',
        # attachment: el navegador ignora <a download> en URLs de otro origen (MinIO)
        Params={
            'Bucket': MINIO_BUCKET,
            'Key': object_name,
            'ResponseContentDisposition': f'attachment; filename="{object_name.rsplit("/", 1)[-1]}"',
        },
        ExpiresIn=expires_in
    )

def ensure_bucket() -> None:
    try:
        s3_client.create_bucket(Bucket=MINIO_BUCKET)
    except (s3_client.exceptions.BucketAlreadyOwnedByYou, s3_client.exceptions.BucketAlreadyExists):
        pass

    # MinIO borra los clips solo pasados N días; idempotente, se reaplica en cada arranque
    s3_client.put_bucket_lifecycle_configuration(
        Bucket=MINIO_BUCKET,
        LifecycleConfiguration={"Rules": [{
            "ID": "expire-clips",
            "Status": "Enabled",
            "Filter": {"Prefix": "clips/"},
            "Expiration": {"Days": CLIP_RETENTION_DAYS},
        }]},
    )
