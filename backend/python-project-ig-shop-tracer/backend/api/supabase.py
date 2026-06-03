import mimetypes
from pathlib import Path, PurePosixPath

import pydantic
from storage3.exceptions import StorageException
from supabase import Client, create_client

from utils.logger import logger

_LOGO_CONTENT_TYPES: dict[str, str] = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
}

_MAX_UPLOAD_BYTES = 1 * 1024 * 1024  # 1 MB


class SupabaseStorageClientConfig(pydantic.BaseModel):
    api_key: str
    project_url: str
    bucket_name: str
    bucket_logo_path: str


class SupabaseStorageService:
    _client: Client
    _bucket_name: str
    _bucket_logo_path: str

    def __init__(self, config: SupabaseStorageClientConfig):
        logger.info("Initiating Supabase api client")
        self._client = create_client(config.project_url, config.api_key)
        self._bucket_name = config.bucket_name
        self._bucket_logo_path = config.bucket_logo_path.strip("/\\")

    def _build_storage_object_path(self, local_file_path: Path) -> str:
        return str(PurePosixPath(self._bucket_logo_path) / local_file_path.name)

    @staticmethod
    def _infer_content_type(file_path: Path) -> str:
        suffix = file_path.suffix.lower()
        if suffix in _LOGO_CONTENT_TYPES:
            return _LOGO_CONTENT_TYPES[suffix]
        guessed_type, _ = mimetypes.guess_type(file_path.name)
        return guessed_type or "application/octet-stream"

    def upload_file(self, src_path: str) -> str:
        """Upload a local file to Supabase storage. Returns the bucket object key."""
        local_file_path = Path(src_path)
        if not local_file_path.is_file():
            raise FileNotFoundError(f"Upload source file not found: {src_path}")

        file_size = local_file_path.stat().st_size
        if file_size > _MAX_UPLOAD_BYTES:
            raise ValueError(
                f"File exceeds 1 MB upload limit ({file_size} bytes): {src_path}"
            )

        storage_object_path = self._build_storage_object_path(local_file_path)
        content_type = self._infer_content_type(local_file_path)
        logger.info(
            "Uploading file to Supabase storage bucket '%s' at '%s' (content-type: %s).",
            self._bucket_name,
            storage_object_path,
            content_type,
        )

        try:
            with local_file_path.open("rb") as file_handle:
                response = (
                    self._client.storage.from_(self._bucket_name)
                    .upload(
                        path=storage_object_path,
                        file=file_handle,
                        file_options={
                            "content-type": content_type,
                            "upsert": "true",
                        },
                    )
                )
        except StorageException as error:
            logger.error(
                "Supabase storage upload failed for '%s': %s",
                storage_object_path,
                error,
            )
            raise

        logger.info(
            "Supabase storage upload succeeded for '%s'. Response: %s",
            storage_object_path,
            response,
        )
        return storage_object_path

    def get_file_url(self, storage_path: str) -> str:
        logger.info("Getting public file URL from Supabase for '%s'.", storage_path)
        public_url = self._client.storage.from_(self._bucket_name).get_public_url(
            storage_path
        )
        logger.info("Supabase public file URL: %s", public_url)
        return public_url
