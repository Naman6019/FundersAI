from __future__ import annotations

import io
import re
from pathlib import Path
from typing import Any

try:
    import boto3  # type: ignore
    from botocore.client import BaseClient  # type: ignore
    from botocore.exceptions import ClientError  # type: ignore
except Exception:  # pragma: no cover - fallback for environments without boto3
    boto3 = None
    BaseClient = Any  # type: ignore

    class ClientError(Exception):
        pass

_SAFE_CHUNK_RE = re.compile(r"[^a-z0-9._-]+")


class R2Store:
    def __init__(
        self,
        *,
        endpoint: str,
        access_key_id: str,
        secret_access_key: str,
        raw_bucket: str,
        cold_bucket: str,
        signed_url_ttl_seconds: int = 300,
    ) -> None:
        self.endpoint = endpoint.strip()
        self.raw_bucket = raw_bucket.strip()
        self.cold_bucket = cold_bucket.strip()
        self.signed_url_ttl_seconds = max(int(signed_url_ttl_seconds or 300), 60)
        self._enabled = bool(self.endpoint and access_key_id and secret_access_key and self.raw_bucket and boto3)
        self._client: BaseClient | None = None
        if self._enabled:
            from botocore.config import Config  # type: ignore
            self._client = boto3.client(
                "s3",
                endpoint_url=self.endpoint,
                aws_access_key_id=access_key_id,
                aws_secret_access_key=secret_access_key,
                region_name="auto",
                config=Config(signature_version="s3v4"),
            )

    @property
    def enabled(self) -> bool:
        return self._enabled and self._client is not None

    def upload_bytes(
        self,
        key: str,
        content: bytes,
        *,
        bucket: str | None = None,
        content_type: str | None = None,
        metadata: dict[str, str] | None = None,
    ) -> dict[str, str]:
        client = self._require_client()
        clean_key = build_safe_key(key)
        target_bucket = self._bucket_or_default(bucket)
        extra_args: dict[str, Any] = {"Metadata": metadata or {}}
        if content_type:
            extra_args["ContentType"] = content_type
        client.upload_fileobj(io.BytesIO(content), target_bucket, clean_key, ExtraArgs=extra_args)
        return {"bucket": target_bucket, "key": clean_key}

    def upload_file(
        self,
        key: str,
        file_path: str | Path,
        *,
        bucket: str | None = None,
        content_type: str | None = None,
        metadata: dict[str, str] | None = None,
    ) -> dict[str, str]:
        path = Path(file_path)
        return self.upload_bytes(
            key,
            path.read_bytes(),
            bucket=bucket,
            content_type=content_type,
            metadata=metadata,
        )

    def download_to_file(self, key: str, local_path: str | Path, *, bucket: str | None = None) -> str:
        client = self._require_client()
        clean_key = build_safe_key(key)
        target_bucket = self._bucket_or_default(bucket)
        path = Path(local_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("wb") as handle:
            client.download_fileobj(target_bucket, clean_key, handle)
        return str(path.resolve())

    def object_exists(self, key: str, *, bucket: str | None = None) -> bool:
        client = self._require_client()
        clean_key = build_safe_key(key)
        target_bucket = self._bucket_or_default(bucket)
        try:
            client.head_object(Bucket=target_bucket, Key=clean_key)
            return True
        except ClientError as exc:
            code = str(exc.response.get("Error", {}).get("Code", "")).lower()
            if code in {"404", "notfound", "nosuchkey"}:
                return False
            raise

    def generate_signed_url(
        self,
        key: str,
        *,
        bucket: str | None = None,
        expires_seconds: int | None = None,
    ) -> str:
        client = self._require_client()
        clean_key = build_safe_key(key)
        target_bucket = self._bucket_or_default(bucket)
        ttl = max(int(expires_seconds or self.signed_url_ttl_seconds), 60)
        return client.generate_presigned_url(
            "get_object",
            Params={"Bucket": target_bucket, "Key": clean_key},
            ExpiresIn=ttl,
        )

    def _require_client(self) -> BaseClient:
        if not self.enabled or self._client is None:
            raise RuntimeError("r2_not_configured")
        return self._client

    def _bucket_or_default(self, bucket: str | None) -> str:
        selected = (bucket or self.raw_bucket).strip()
        if not selected:
            raise RuntimeError("r2_bucket_not_configured")
        return selected


def build_safe_key(*parts: object) -> str:
    if not parts:
        raise ValueError("r2_key_parts_required")
    chunks: list[str] = []
    for raw in parts:
        text = str(raw or "").replace("\\", "/").strip().lower()
        if not text:
            continue
        for piece in text.split("/"):
            clean = _sanitize_chunk(piece)
            if clean:
                chunks.append(clean)
    if not chunks:
        raise ValueError("r2_key_empty_after_sanitize")
    return "/".join(chunks)


def _sanitize_chunk(value: str) -> str:
    value = value.strip()
    if value in {"", ".", ".."}:
        return ""
    cleaned = _SAFE_CHUNK_RE.sub("-", value)
    cleaned = cleaned.replace("..", "-").strip("-.")
    return cleaned
