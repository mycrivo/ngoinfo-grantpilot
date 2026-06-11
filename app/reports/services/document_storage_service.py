from __future__ import annotations

import uuid
from pathlib import PurePosixPath

import boto3
from botocore.client import BaseClient
from botocore.exceptions import BotoCoreError, ClientError

from app.core.config import Settings, get_settings


class DocumentStorageError(Exception):
    """Raised when object storage read/write/delete fails."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class DocumentStorageService:
    """S3-compatible storage for M&E uploaded documents (Railway Buckets)."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._client: BaseClient | None = None
        self._validate_config()

    def _validate_config(self) -> None:
        required = {
            "ME_DOCUMENTS_S3_ENDPOINT": self._settings.ME_DOCUMENTS_S3_ENDPOINT,
            "ME_DOCUMENTS_S3_ACCESS_KEY": self._settings.ME_DOCUMENTS_S3_ACCESS_KEY,
            "ME_DOCUMENTS_S3_SECRET": self._settings.ME_DOCUMENTS_S3_SECRET,
            "ME_DOCUMENTS_S3_BUCKET": self._settings.ME_DOCUMENTS_S3_BUCKET,
        }
        missing = [name for name, value in required.items() if not value.strip()]
        if missing:
            raise RuntimeError(
                "Document storage is not configured. Missing: "
                + ", ".join(missing)
            )

    @property
    def bucket(self) -> str:
        return self._settings.ME_DOCUMENTS_S3_BUCKET

    @property
    def client(self) -> BaseClient:
        if self._client is None:
            self._client = boto3.client(
                "s3",
                endpoint_url=self._settings.ME_DOCUMENTS_S3_ENDPOINT,
                aws_access_key_id=self._settings.ME_DOCUMENTS_S3_ACCESS_KEY,
                aws_secret_access_key=self._settings.ME_DOCUMENTS_S3_SECRET,
            )
        return self._client

    @staticmethod
    def build_storage_ref(
        user_id: uuid.UUID, report_id: uuid.UUID, filename: str
    ) -> str:
        safe_name = PurePosixPath(filename).name.replace(" ", "_")
        return f"users/{user_id}/reports/{report_id}/{uuid.uuid4()}/{safe_name}"

    def upload_bytes(self, key: str, data: bytes, content_type: str) -> None:
        self.client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
        )

    def fetch_bytes(self, key: str) -> bytes:
        response = self.client.get_object(Bucket=self.bucket, Key=key)
        return response["Body"].read()

    def delete_object(self, key: str) -> None:
        try:
            self.client.delete_object(Bucket=self.bucket, Key=key)
        except (ClientError, BotoCoreError) as exc:
            raise DocumentStorageError(
                "STORAGE_DELETE_FAILED",
                f"Failed to delete object {key}: {exc}",
            ) from exc
