"""
shared/cos_client.py
─────────────────────
IBM Cloud Object Storage helpers using the ibm-cos-sdk (boto3-compatible).

Provides:
  upload_object()   — upload bytes/string to a COS bucket
  download_object() — download an object and return bytes
  object_exists()   — check if a key exists without downloading

Usage:
    upload_object(settings, settings.cos_bucket_artefacts, "designs/abc.json", content)
    data = download_object(settings, settings.cos_bucket_artefacts, "designs/abc.json")
"""

from functools import lru_cache
from typing import Union

import ibm_boto3
from ibm_botocore.client import Config

from shared.config import Settings
from shared.exceptions import COSUploadError
from shared.logging import get_logger

logger = get_logger(__name__)


@lru_cache(maxsize=1)
def _get_cos_resource(endpoint: str, api_key: str, instance_id: str):
    """Return a cached ibm_boto3 resource."""
    return ibm_boto3.resource(
        "s3",
        ibm_api_key_id=api_key,
        ibm_service_instance_id=instance_id,
        config=Config(signature_version="oauth"),
        endpoint_url=endpoint,
    )


def upload_object(
    settings: Settings,
    bucket: str,
    key: str,
    body: Union[str, bytes],
    content_type: str = "application/json",
) -> str:
    """
    Upload an object to IBM COS.

    Returns the full COS URI: cos://<bucket>/<key>
    Raises COSUploadError on failure.
    """
    if isinstance(body, str):
        body = body.encode("utf-8")
    cos = _get_cos_resource(settings.cos_endpoint, settings.cos_api_key, settings.cos_instance_id)
    try:
        cos.Object(bucket, key).put(Body=body, ContentType=content_type)
        uri = f"cos://{bucket}/{key}"
        logger.info("COS upload success", extra={"bucket": bucket, "key": key, "bytes": len(body)})
        return uri
    except Exception as exc:
        raise COSUploadError(bucket=bucket, key=key) from exc


def download_object(settings: Settings, bucket: str, key: str) -> bytes:
    """Download an object from IBM COS and return raw bytes."""
    cos = _get_cos_resource(settings.cos_endpoint, settings.cos_api_key, settings.cos_instance_id)
    obj = cos.Object(bucket, key).get()
    return obj["Body"].read()


def object_exists(settings: Settings, bucket: str, key: str) -> bool:
    """Return True if the key exists in the bucket."""
    cos = _get_cos_resource(settings.cos_endpoint, settings.cos_api_key, settings.cos_instance_id)
    try:
        cos.Object(bucket, key).load()
        return True
    except Exception:
        return False
