import os
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Any
from uuid import uuid4

from fastapi import BackgroundTasks, FastAPI, HTTPException
from storage3.exceptions import StorageException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from ai.providers.gemini import GeminiClientConfig, GeminiService
from ai.services.store import StoreAIService
from dtos.bookmarks import BookmarksDTO
from schemas.settings import ClientSettings
from dtos.store import StoreDTO
from models.collections import CollectionName
from services.database import close_mongo_connection, get_mongo_db
from services.bookmarks import add_store_to_bookmark
from services.bookmarks import create_bookmark as create_bookmark_in_db
from services.bookmarks import get_bookmarks as get_bookmarks_from_db
from services.bookmarks import remove_store_from_bookmarks
from models.store import Store
from pymongo.collection import Collection
from schemas.bookmarks import BookmarksAdd
from schemas.base import ResponseBase
from schemas.store import StoreAdd, StoreAIGenerate, StoreDelete, StoreRenew
from utils.logger import logger
from config.settings import settings
from services.store import (
    create_store,
    download_store_logo,
    get_store_by_api_id,
    get_store_by_username,
    map_store_from_rapid_api_result,
    store_info_generation_task,
)
from api.rapid import request_rapid_api_profile
from api.supabase import SupabaseStorageClientConfig, SupabaseStorageService

# Global env var
RAPID_API_KEY = settings.RAPID_API_KEY
GEMINI_API_KEY = settings.GEMINI_API_KEY
GEMINI_MODEL = settings.GEMINI_MODEL
STORE_LOGOS_FOLDER_PATH = settings.STORE_LOGOS_FOLDER_PATH
LOGS_FOLDER_PATH = settings.LOGS_FOLDER_PATH

# Main app logic
@asynccontextmanager
async def lifespan(application: FastAPI):
    mongo_db = get_mongo_db()
    stores_collection = mongo_db[CollectionName.STORE.value]

    # Connection check should fail fast on startup if db is not reachable.
    mongo_db.command("ping")
    STORE_LOGOS_FOLDER_PATH.mkdir(parents=True, exist_ok=True)

    application.state.mongo_db = mongo_db
    application.state.stores_collection = stores_collection
    gemini_client = GeminiService(
        GeminiClientConfig(api_key=GEMINI_API_KEY, model=GEMINI_MODEL),
        logger=logger,
    )
    application.state.gemini_client = gemini_client
    application.state.store_ai_service = StoreAIService(gemini_client)
    supabase_storage_service = SupabaseStorageService(SupabaseStorageClientConfig(
        api_key=settings.SUPABASE_API_KEY,
        project_url=settings.SUPABASE_PROJECT_URL,
        bucket_name=settings.SUPABASE_STORAGE_BUCKET_NAME,
        bucket_logo_path=settings.SUPABASE_STORAGE_BUCKET_LOGO_PATH,
    ))
    application.state.supabase_storage_service = supabase_storage_service

    yield
    close_mongo_connection()

app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Path operation logic
@app.get("/settings", response_model=ClientSettings)
async def get_client_settings() -> ClientSettings:
    return ClientSettings(
        googleMapsApiKey=os.getenv("GOOGLE_MAPS_API_KEY", ""),
    )


@app.post("/create_bookmark")
async def create_bookmark(payload: BookmarksAdd) -> ResponseBase[dict[str, str]]:
    bookmarks_uuid = payload.uuid.strip()
    response_payload = {"uuid": bookmarks_uuid}
    created_bookmarks, error_message = create_bookmark_in_db(bookmarks_uuid)
    if created_bookmarks is None:
        return ResponseBase[dict[str, str]](
            payload=response_payload,
            success=False,
            message=error_message or "Bookmarks create failed.",
        )

    return ResponseBase[dict[str, str]](
        payload=response_payload,
        success=True,
        message="Bookmarks were created successfully.",
        data={"uuid": created_bookmarks.uuid},
    )


@app.get("/get_bookmarks/{bookmarks_uuid}")
async def get_bookmarks(bookmarks_uuid: str) -> ResponseBase[BookmarksDTO]:
    normalized_uuid = bookmarks_uuid.strip()
    response_payload = {"uuid": normalized_uuid}
    bookmarks_data, error_message = get_bookmarks_from_db(normalized_uuid)
    if bookmarks_data is None:
        return ResponseBase[BookmarksDTO](
            payload=response_payload,
            success=False,
            message=error_message or "Bookmarks lookup failed.",
        )

    return ResponseBase[BookmarksDTO](
        payload=response_payload,
        success=True,
        message="Bookmarks lookup successful.",
        data=bookmarks_data,
    )


@app.get("/store_profile/{username}", response_model=StoreDTO)
async def get_store_profile(username: str) -> StoreDTO:
    store, error_message, mongo_object_id = get_store_by_username(username)
    if store is None:
        if error_message == "Store not found.":
            raise HTTPException(status_code=404, detail="Store profile not found.")
        raise HTTPException(status_code=400, detail=error_message or "Unable to load store profile.")

    return StoreDTO.from_store(store, object_id=mongo_object_id)


@app.post("/add_store")
async def add_store_profile(
    payload: StoreAdd,
    background_tasks: BackgroundTasks,
) -> ResponseBase[Store]:
    """Add an Instagram store to a user's bookmark list."""
    page_name = payload.username.strip()
    ctx = _AddStoreRequestContext(
        trace_id=str(uuid4()),
        started_at=perf_counter(),
        page_name=page_name,
        bookmarks_uuid=payload.uuid.strip(),
        response_payload={"query_store_name": page_name},
    )
    logger.info(
        "[trace_id=%s] Add store request started for username '%s'.",
        ctx.trace_id,
        ctx.page_name,
    )

    if validation_error := _validate_add_store_input(
        ctx.page_name,
        ctx.bookmarks_uuid,
        ctx.response_payload,
    ):
        return validation_error

    if existing_response := _try_bookmark_existing_store_by_username(ctx):
        return existing_response

    mapped_profile, fetch_error = await _fetch_store_from_rapid_api(ctx)
    if fetch_error is not None:
        return fetch_error

    return await _create_store_and_bookmark(
        mapped_profile,
        ctx,
        background_tasks,
        app.state.gemini_client,
        app.state.supabase_storage_service,
    )


@app.post("/renew_store")
async def renew_store_profile(payload: StoreRenew) -> ResponseBase[Store]:
    """Refresh an existing store document from Instagram profile data."""
    page_name = payload.username.strip().lstrip("@")
    ctx = _StoreUsernameRequestContext(
        trace_id=str(uuid4()),
        started_at=perf_counter(),
        page_name=page_name,
        response_payload={"query_store_name": page_name},
    )
    logger.info(
        "[trace_id=%s] Renew store request started for username '%s'.",
        ctx.trace_id,
        ctx.page_name,
    )

    if page_name == "":
        return ResponseBase[Store](
            payload=ctx.response_payload,
            success=False,
            message=(
                "Store renew rejected: username is required. "
                "Provide a valid Instagram username and try again."
            ),
        )

    return await _renew_store_profile(
        ctx,
        app.state.supabase_storage_service,
    )


@app.post("/delete_store")
async def delete_store_profile(payload: StoreDelete) -> ResponseBase[dict[str, str]]:
    bookmarks_uuid = payload.uuid.strip()
    store_id = payload.store_id.strip()
    response_payload = {"uuid": bookmarks_uuid, "store_id": store_id}

    if bookmarks_uuid == "":
        return ResponseBase[dict[str, str]](
            payload=response_payload,
            success=False,
            message="Store delete rejected: bookmarks uuid is required.",
        )
    if store_id == "":
        return ResponseBase[dict[str, str]](
            payload=response_payload,
            success=False,
            message="Store delete rejected: store id is required.",
        )

    removed, error_message = remove_store_from_bookmarks(
        bookmarks_uuid=bookmarks_uuid,
        store_id=store_id,
    )
    if not removed:
        return ResponseBase[dict[str, str]](
            payload=response_payload,
            success=False,
            message=error_message or "Store delete failed.",
        )

    return ResponseBase[dict[str, str]](
        payload=response_payload,
        success=True,
        message="Store removed from bookmarks successfully.",
        data={"uuid": bookmarks_uuid, "store_id": store_id},
    )


# internal functions
@dataclass(frozen=True)
class _StoreUsernameRequestContext:
    trace_id: str
    started_at: float
    page_name: str
    response_payload: dict[str, str]

    def elapsed_ms(self) -> float:
        return (perf_counter() - self.started_at) * 1000


@dataclass(frozen=True)
class _AddStoreRequestContext(_StoreUsernameRequestContext):
    bookmarks_uuid: str


def _validate_add_store_input(
    page_name: str,
    bookmarks_uuid: str,
    response_payload: dict[str, str],
) -> ResponseBase[Store] | None:
    if page_name == "":
        return ResponseBase[Store](
            payload=response_payload,
            success=False,
            message=(
                "Instagram store lookup rejected: username is required. "
                "Provide a valid Instagram username and try again."
            ),
        )
    if bookmarks_uuid == "":
        return ResponseBase[Store](
            payload=response_payload,
            success=False,
            message="Store add rejected: bookmarks uuid is required.",
        )
    return None


def _bookmark_link_failure_message(bookmark_error: str | None) -> str:
    if bookmark_error == "Bookmarks not found.":
        return (
            "Store already exists, but bookmarks document was not found "
            "for the provided uuid."
        )
    return bookmark_error or "Unable to add store to bookmarks."


def _link_store_to_bookmarks(
    store: Store,
    mongo_object_id: str,
    ctx: _AddStoreRequestContext,
    completion_log: str,
) -> ResponseBase[Store]:
    if mongo_object_id == "":
        return ResponseBase[Store](
            payload=ctx.response_payload,
            success=False,
            message="Store exists but has no valid object id for bookmark linkage.",
        )

    bookmarked, bookmark_error, already_bookmarked = add_store_to_bookmark(
        mongo_object_id,
        ctx.bookmarks_uuid,
    )
    if not bookmarked:
        logger.warning(
            "[trace_id=%s] Add store request failed: %s in %.2f ms.",
            ctx.trace_id,
            bookmark_error or "bookmark update failed",
            ctx.elapsed_ms(),
        )
        return ResponseBase[Store](
            payload=ctx.response_payload,
            success=False,
            message=_bookmark_link_failure_message(bookmark_error),
        )

    logger.info("[trace_id=%s] %s in %.2f ms.", ctx.trace_id, completion_log, ctx.elapsed_ms())
    return ResponseBase[Store](
        payload=ctx.response_payload,
        success=True,
        message=(
            "Store already bookmarked."
            if already_bookmarked
            else "Store was added to bookmarks."
        ),
        data=store,
    )


def _try_bookmark_existing_store_by_username(
    ctx: _AddStoreRequestContext,
) -> ResponseBase[Store] | None:
    existing_store, _, mongo_object_id = get_store_by_username(ctx.page_name)
    if existing_store is None:
        return None
    return _link_store_to_bookmarks(
        existing_store,
        mongo_object_id,
        ctx,
        completion_log=(
            f"Add store request used existing store document for username '{ctx.page_name}'"
        ),
    )


async def _fetch_store_from_rapid_api(
    ctx: _StoreUsernameRequestContext,
    request_label: str = "Add store",
) -> tuple[Store | None, ResponseBase[Store] | None]:
    result, error_message = await request_rapid_api_profile(ctx.page_name, trace_id=ctx.trace_id)
    if result is None:
        logger.warning(
            "[trace_id=%s] %s request failed during profile lookup for username '%s' in %.2f ms.",
            ctx.trace_id,
            request_label,
            ctx.page_name,
            ctx.elapsed_ms(),
        )
        return None, ResponseBase[Store](
            payload=ctx.response_payload,
            success=False,
            message=error_message or "Instagram store lookup failed: unknown error.",
        )

    mapped_profile = map_store_from_rapid_api_result(result)
    if mapped_profile.id == "":
        return None, ResponseBase[Store](
            payload=ctx.response_payload,
            success=False,
            message=(
                "Instagram store lookup completed but no usable profile was found. "
                "Verify the username and ensure the account is accessible."
            ),
        )
    return mapped_profile, None


def _upload_store_logo_to_supabase(
    supabase_storage_service: SupabaseStorageService,
    downloaded_logo_route_path: str,
    trace_id: str,
) -> tuple[str | None, str | None]:
    logo_filename = Path(downloaded_logo_route_path).name
    if logo_filename == "":
        return None, "Logo upload failed: invalid local logo path."

    logo_absolute_path = STORE_LOGOS_FOLDER_PATH / logo_filename
    try:
        storage_object_path = supabase_storage_service.upload_file(str(logo_absolute_path))
        public_url = supabase_storage_service.get_file_url(storage_object_path)
        logger.info(
            "[trace_id=%s] Store logo uploaded to Supabase at '%s'.",
            trace_id,
            storage_object_path,
        )
        return public_url, None
    except FileNotFoundError:
        logger.warning(
            "[trace_id=%s] Logo upload failed: local file not found at '%s'.",
            trace_id,
            logo_absolute_path,
        )
        return None, "Logo upload failed: local logo file was not found."
    except ValueError as error:
        logger.warning(
            "[trace_id=%s] Logo upload rejected for '%s': %s",
            trace_id,
            logo_absolute_path,
            error,
        )
        return None, f"Logo upload failed: {error}"
    except StorageException as error:
        logger.warning(
            "[trace_id=%s] Logo upload failed for '%s': %s",
            trace_id,
            logo_absolute_path,
            error,
        )
        return None, "Logo upload failed: Supabase storage returned an error."


async def _fetch_and_upload_store_logo(
    mapped_profile: Store,
    ctx: _StoreUsernameRequestContext,
    supabase_storage_service: SupabaseStorageService,
    request_label: str,
) -> tuple[Store | None, ResponseBase[Store] | None]:
    downloaded_logo_route, logo_download_error = await download_store_logo(
        logo_url=mapped_profile.hd_profile_pic_url,
        store_id=mapped_profile.id,
        trace_id=ctx.trace_id,
    )
    if downloaded_logo_route is None:
        logger.warning(
            "[trace_id=%s] %s request failed during logo download for username '%s' in %.2f ms.",
            ctx.trace_id,
            request_label,
            ctx.page_name,
            ctx.elapsed_ms(),
        )
        return None, ResponseBase[Store](
            payload=ctx.response_payload,
            success=False,
            message=logo_download_error or "Logo image download failed.",
            data=mapped_profile,
        )

    logo_public_url, logo_upload_error = _upload_store_logo_to_supabase(
        supabase_storage_service,
        downloaded_logo_route,
        ctx.trace_id,
    )
    if logo_public_url is None:
        logger.warning(
            "[trace_id=%s] %s request failed during logo upload for username '%s' in %.2f ms.",
            ctx.trace_id,
            request_label,
            ctx.page_name,
            ctx.elapsed_ms(),
        )
        return None, ResponseBase[Store](
            payload=ctx.response_payload,
            success=False,
            message=logo_upload_error or "Logo image upload failed.",
            data=mapped_profile,
        )

    mapped_profile.logo_image_url = logo_public_url
    return mapped_profile, None


def _merge_existing_store_fields_for_renew(
    mapped_profile: Store,
    existing_store: Store,
) -> Store:
    mapped_profile.description = existing_store.description
    mapped_profile.tags = existing_store.tags
    mapped_profile.store_locations = existing_store.store_locations
    mapped_profile.addresses = existing_store.addresses
    mapped_profile.created_at = existing_store.created_at
    return mapped_profile


async def _renew_store_profile(
    ctx: _StoreUsernameRequestContext,
    supabase_storage_service: SupabaseStorageService,
) -> ResponseBase[Store]:
    existing_store, _, _ = get_store_by_username(ctx.page_name)
    if existing_store is None:
        logger.info(
            "[trace_id=%s] Renew store request skipped: no store document for username '%s' in %.2f ms.",
            ctx.trace_id,
            ctx.page_name,
            ctx.elapsed_ms(),
        )
        return ResponseBase[Store](
            payload=ctx.response_payload,
            success=False,
            message="No store data found.",
        )

    mapped_profile, fetch_error = await _fetch_store_from_rapid_api(
        ctx,
        request_label="Renew store",
    )
    if fetch_error is not None:
        return fetch_error

    mapped_profile_with_logo, logo_error = await _fetch_and_upload_store_logo(
        mapped_profile,
        ctx,
        supabase_storage_service,
        request_label="Renew store",
    )
    if logo_error is not None:
        return logo_error

    mapped_profile = _merge_existing_store_fields_for_renew(
        mapped_profile_with_logo,
        existing_store,
    )

    saved, save_error = create_store(mapped_profile.model_dump(), logger)
    if not saved:
        logger.warning(
            "[trace_id=%s] Renew store request failed during database update for username '%s' in %.2f ms.",
            ctx.trace_id,
            ctx.page_name,
            ctx.elapsed_ms(),
        )
        return ResponseBase[Store](
            payload=ctx.response_payload,
            success=False,
            message=(
                "Instagram store lookup succeeded, but renewing profile data in database failed. "
                f"{save_error or 'Please try again later.'}"
            ),
            data=mapped_profile,
        )

    renewed_store, _, _ = get_store_by_username(ctx.page_name)
    response_store = renewed_store if renewed_store is not None else mapped_profile
    logger.info(
        "[trace_id=%s] Renew store request completed successfully for username '%s' in %.2f ms.",
        ctx.trace_id,
        ctx.page_name,
        ctx.elapsed_ms(),
    )
    return ResponseBase[Store](
        payload=ctx.response_payload,
        success=True,
        message="Store profile renewed successfully.",
        data=response_store,
    )


async def _create_store_and_bookmark(
    mapped_profile: Store,
    ctx: _AddStoreRequestContext,
    background_tasks: BackgroundTasks,
    gemini_client: GeminiService,
    supabase_storage_service: SupabaseStorageService,
) -> ResponseBase[Store]:
    mapped_profile_with_logo, logo_error = await _fetch_and_upload_store_logo(
        mapped_profile,
        ctx,
        supabase_storage_service,
        request_label="Add store",
    )
    if logo_error is not None:
        return logo_error
    mapped_profile = mapped_profile_with_logo

    saved, save_error = create_store(mapped_profile.model_dump(), logger)
    if not saved:
        logger.warning(
            "[trace_id=%s] Add store request failed during database insert for username '%s' in %.2f ms.",
            ctx.trace_id,
            ctx.page_name,
            ctx.elapsed_ms(),
        )
        return ResponseBase[Store](
            payload=ctx.response_payload,
            success=False,
            message=(
                "Instagram store lookup succeeded, but persisting profile data to database failed. "
                f"{save_error or 'Please try again later.'}"
            ),
            data=mapped_profile,
        )

    _, _, mongo_object_id = get_store_by_api_id(mapped_profile.id)
    bookmarked, bookmark_error, _ = add_store_to_bookmark(mongo_object_id, ctx.bookmarks_uuid)
    if not bookmarked:
        logger.warning(
            "[trace_id=%s] Add store request failed: bookmarks not found for uuid '%s' in %.2f ms.",
            ctx.trace_id,
            ctx.bookmarks_uuid,
            ctx.elapsed_ms(),
        )
        return ResponseBase[Store](
            payload=ctx.response_payload,
            success=False,
            message=(
                bookmark_error
                or "Store profile was saved, but bookmarks document was not found for the provided uuid."
            ),
            data=mapped_profile,
        )

    background_tasks.add_task(store_info_generation_task, gemini_client, ctx.page_name)
    logger.info(
        "[trace_id=%s] Add store request completed successfully for username '%s' in %.2f ms.",
        ctx.trace_id,
        ctx.page_name,
        ctx.elapsed_ms(),
    )
    return ResponseBase[Store](
        payload=ctx.response_payload,
        success=True,
        message="Store profile added and bookmarked successfully.",
        data=mapped_profile,
    )


# testing operations
@app.post("/ai_generate_store_info")
async def ai_generate_store_info(
    payload: StoreAIGenerate,
    background_tasks: BackgroundTasks,
) -> ResponseBase[StoreDTO]:
    page_name = payload.username.strip().lstrip("@")
    response_payload = {"query_store_name": page_name}

    if page_name == "":
        return ResponseBase[StoreDTO](
            payload=response_payload,
            success=False,
            message="Store AI generate rejected: username is required. Provide a valid Instagram username and try again.",
        )

    background_tasks.add_task(store_info_generation_task, page_name)
    return ResponseBase[StoreDTO](
        payload=response_payload,
        success=True,
        message="Store AI generation started in the background.",
    )


@app.get("/profile/{page_name}")
async def get_page_profile(page_name: str):
    result, _ = await request_rapid_api_profile(page_name)
    return result


@app.get("/stores", response_model=list[StoreDTO])
async def get_store_items(skip: int = 0, limit: int = 0) -> list[StoreDTO]:
    start_index = max(skip, 0)
    stores_collection: Collection[Any] = app.state.stores_collection

    cursor = stores_collection.find({}, {"_id": 0})
    cursor = cursor.skip(start_index)
    if limit > 0:
        cursor = cursor.limit(limit)

    records = list(cursor)
    mapped_items: list[StoreDTO] = []
    for record in records:
        source_record = dict(record)
        mongo_object_id = str(source_record.pop("_id", "") or "")
        mapped_items.append(
            StoreDTO.from_store(Store(**source_record), object_id=mongo_object_id)
        )
    return mapped_items

@app.get("/health/db")
async def database_health_check() -> dict[str, str]:
    mongo_db = get_mongo_db()
    mongo_db.command("ping")
    return {"status": "ok"}


# Mounted after API routes so /store_logos does not shadow dynamic endpoints.
app.mount(
    "/store_logos",
    StaticFiles(directory=STORE_LOGOS_FOLDER_PATH),
    name="store_logos",
)