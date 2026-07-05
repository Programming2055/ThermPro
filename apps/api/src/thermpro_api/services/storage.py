"""Object storage interface and MinIO/S3 implementation."""
from __future__ import annotations

import abc
import io
from typing import Any

import boto3
import botocore.exceptions

from thermpro_api.settings import get_settings


class ObjectStorage(abc.ABC):
    """Abstract interface for object (blob) storage."""

    @abc.abstractmethod
    def put_object(
        self,
        key: str,
        data: bytes,
        content_type: str = "application/octet-stream",
        metadata: dict[str, str] | None = None,
    ) -> None:
        """Upload *data* to object storage at *key*."""
        raise NotImplementedError

    @abc.abstractmethod
    def get_object(self, key: str) -> bytes:
        """Download and return the bytes stored at *key*."""
        raise NotImplementedError

    @abc.abstractmethod
    def delete_object(self, key: str) -> None:
        """Delete the object at *key*. No-op if the key does not exist."""
        raise NotImplementedError

    @abc.abstractmethod
    def get_presigned_url(self, key: str, expires_in_seconds: int = 3600) -> str:
        """Return a pre-signed GET URL valid for *expires_in_seconds* seconds."""
        raise NotImplementedError


class MinIOStorage(ObjectStorage):
    """boto3-based implementation targeting MinIO (S3-compatible)."""

    def __init__(self) -> None:
        settings = get_settings()
        self._bucket = settings.s3_bucket_artifacts
        self._client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            aws_access_key_id=settings.s3_access_key_id,
            aws_secret_access_key=settings.s3_secret_access_key,
            region_name=settings.s3_region,
        )

    def put_object(
        self,
        key: str,
        data: bytes,
        content_type: str = "application/octet-stream",
        metadata: dict[str, str] | None = None,
    ) -> None:
        kwargs: dict[str, Any] = {
            "Bucket": self._bucket,
            "Key": key,
            "Body": io.BytesIO(data),
            "ContentType": content_type,
        }
        if metadata:
            kwargs["Metadata"] = metadata
        self._client.put_object(**kwargs)

    def get_object(self, key: str) -> bytes:
        response = self._client.get_object(Bucket=self._bucket, Key=key)
        return response["Body"].read()  # type: ignore[no-any-return]

    def delete_object(self, key: str) -> None:
        import contextlib
        with contextlib.suppress(botocore.exceptions.ClientError):
            self._client.delete_object(Bucket=self._bucket, Key=key)

    def get_presigned_url(self, key: str, expires_in_seconds: int = 3600) -> str:
        return self._client.generate_presigned_url(  # type: ignore[no-any-return]
            "get_object",
            Params={"Bucket": self._bucket, "Key": key},
            ExpiresIn=expires_in_seconds,
        )


_storage_instance: ObjectStorage | None = None


def get_storage() -> ObjectStorage:
    """FastAPI dependency: return the singleton ObjectStorage instance."""
    global _storage_instance
    if _storage_instance is None:
        _storage_instance = MinIOStorage()
    return _storage_instance
