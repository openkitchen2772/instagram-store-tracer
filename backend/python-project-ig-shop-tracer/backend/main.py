import os
from contextlib import asynccontextmanager
from time import perf_counter
from typing import Any
from uuid import uuid4

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from ai.providers.gemini import GeminiClientConfig, GeminiService
from ai.services.store import StoreAIService
from dtos.bookmarks import BookmarksDTO
from schemas.settings import ClientSettings
from dtos.store import StoreDTO
from models.collections import CollectionName
from services.database import close_mongo_connection, get_mongo_db
from services.bookmarks import create_bookmark as create_bookmark_in_db
from services.bookmarks import get_bookmarks as get_bookmarks_from_db
from services.bookmarks import remove_store_from_bookmarks
from models.store import Store
from pymongo.collection import Collection
from pymongo.errors import PyMongoError
from schemas.bookmarks import BookmarksAdd
from schemas.base import ResponseBase
from schemas.store import StoreAdd, StoreAIGenerate, StoreDelete
from utils.logger import logger
from config.settings import settings
from services.store import download_store_logo
from api.rapid import request_rapid_api_profile
from services.store import store_info_generation_task

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
@app.get("/store_profile/{username}", response_model=StoreDTO)
async def get_store_profile(username: str) -> StoreDTO:
    normalized_username = username.strip().lstrip("@")
    if normalized_username == "":
        raise HTTPException(status_code=400, detail="Username is required.")

    stores_collection: Collection[Any] = app.state.stores_collection
    logger.info(
        "Store profile lookup started for username '%s'.",
        normalized_username,
    )
    store_record = stores_collection.find_one({"username": normalized_username})
    if store_record is None:
        logger.info(
            "Store profile lookup returned no document for username '%s'.",
            normalized_username,
        )
        raise HTTPException(status_code=404, detail="Store profile not found.")

    source_record = dict(store_record)
    mongo_object_id = str(source_record.pop("_id", "") or "")
    logger.info(
        "Store profile lookup succeeded for username '%s' with object_id '%s'.",
        normalized_username,
        mongo_object_id,
    )
    return StoreDTO.from_store(Store(**source_record), object_id=mongo_object_id)


@app.get("/settings", response_model=ClientSettings)
async def get_client_settings() -> ClientSettings:
    return ClientSettings(
        googleMapsApiKey=os.getenv("GOOGLE_MAPS_API_KEY", ""),
    )

@app.post("/create_bookmark")
async def create_bookmark(payload: BookmarksAdd) -> ResponseBase[dict[str, str]]:
    bookmarks_uuid = payload.uuid.strip()
    response_payload = {"uuid": bookmarks_uuid}
    created_bookmarks, error_message = create_bookmark_in_db(
        bookmarks_uuid=bookmarks_uuid,
        logger=logger,
    )
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
    bookmarks_data, error_message = get_bookmarks_from_db(
        bookmarks_uuid=normalized_uuid,
        logger=logger,
    )
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

@app.post("/add_store")
async def add_store_profile(
    payload: StoreAdd,
    background_tasks: BackgroundTasks,
) -> ResponseBase[Store]:
    add_store_started_at = perf_counter()
    trace_id = str(uuid4())
    page_name = payload.username.strip()
    bookmarks_uuid = payload.uuid.strip()
    response_payload = {"query_store_name": page_name}
    logger.info("[trace_id=%s] Add store request started for username '%s'.", trace_id, page_name)

    if page_name == "":
        return ResponseBase[Store](
            payload=response_payload,
            success=False,
            message="Instagram store lookup rejected: username is required. Provide a valid Instagram username and try again.",
        )
    if bookmarks_uuid == "":
        return ResponseBase[Store](
            payload=response_payload,
            success=False,
            message="Store add rejected: bookmarks uuid is required.",
        )

    mongo_db = get_mongo_db()
    stores_collection = mongo_db[CollectionName.STORE.value]
    logger.info(
        "[trace_id=%s] Checking for existing store by username '%s' before external profile lookup.",
        trace_id,
        page_name,
    )
    existing_store_by_username = stores_collection.find_one({"username": page_name})
    if existing_store_by_username is not None:
        existing_store_object_id = existing_store_by_username.get("_id")
        if existing_store_object_id is None:
            return ResponseBase[Store](
                payload=response_payload,
                success=False,
                message="Store exists but has no valid object id for bookmark linkage.",
            )
        bookmarks_collection = mongo_db[CollectionName.BOOKMARKS.value]
        bookmark_update_result = bookmarks_collection.update_one(
            {"uuid": bookmarks_uuid},
            {"$addToSet": {"store_ids": existing_store_object_id}},
        )
        if bookmark_update_result.matched_count == 0:
            total_elapsed_ms = (perf_counter() - add_store_started_at) * 1000
            logger.warning(
                "[trace_id=%s] Add store request failed: bookmarks not found for uuid '%s' in %.2f ms.",
                trace_id,
                bookmarks_uuid,
                total_elapsed_ms,
            )
            return ResponseBase[Store](
                payload=response_payload,
                success=False,
                message="Store already exists, but bookmarks document was not found for the provided uuid.",
            )

        existing_store_without_object_id = dict(existing_store_by_username)
        existing_store_without_object_id.pop("_id", None)
        total_elapsed_ms = (perf_counter() - add_store_started_at) * 1000
        logger.info(
            "[trace_id=%s] Add store request used existing store document for username '%s' in %.2f ms.",
            trace_id,
            page_name,
            total_elapsed_ms,
        )
        return ResponseBase[Store](
            payload=response_payload,
            success=True,
            message="Store already bookmarked." if bookmark_update_result.modified_count == 0 else "Store was added to bookmarks.",
            data=Store(**existing_store_without_object_id),
        )

    result, error_message = await request_rapid_api_profile(page_name, trace_id=trace_id)
    if result is None:
        total_elapsed_ms = (perf_counter() - add_store_started_at) * 1000
        logger.warning(
            "[trace_id=%s] Add store request failed during profile lookup for username '%s' in %.2f ms.",
            trace_id,
            page_name,
            total_elapsed_ms,
        )
        return ResponseBase[Store](
            payload=response_payload,
            success=False,
            message=error_message or "Instagram store lookup failed: unknown error.",
        )

    source_profile: dict[str, Any] = result
    result_container = result.get("result")
    if isinstance(result_container, list) and len(result_container) > 0 and isinstance(result_container[0], dict):
        candidate_user = result_container[0].get("user")
        if isinstance(candidate_user, dict):
            source_profile = candidate_user
        else:
            source_profile = result_container[0]
    elif isinstance(result_container, dict):
        candidate_user = result_container.get("user")
        if isinstance(candidate_user, dict):
            source_profile = candidate_user
        else:
            source_profile = result_container

    mapped_profile = Store()
    mapped_profile.update_from_source_profile(source_profile)

    if mapped_profile.id == "":
        return ResponseBase[Store](
            payload=response_payload,
            success=False,
            message="Instagram store lookup completed but no usable profile was found. Verify the username and ensure the account is accessible.",
        )

    existing_profile = stores_collection.find_one({"id": mapped_profile.id})
    if existing_profile is not None:
        existing_store_object_id = existing_profile.get("_id")
        if existing_store_object_id is None:
            return ResponseBase[Store](
                payload=response_payload,
                success=False,
                message="Store exists but has no valid object id for bookmark linkage.",
            )
        bookmarks_collection = mongo_db[CollectionName.BOOKMARKS.value]
        bookmark_update_result = bookmarks_collection.update_one(
            {"uuid": bookmarks_uuid},
            {"$addToSet": {"store_ids": existing_store_object_id}},
        )
        if bookmark_update_result.matched_count == 0:
            total_elapsed_ms = (perf_counter() - add_store_started_at) * 1000
            logger.warning(
                "[trace_id=%s] Add store request failed: bookmarks not found for uuid '%s' in %.2f ms.",
                trace_id,
                bookmarks_uuid,
                total_elapsed_ms,
            )
            return ResponseBase[Store](
                payload=response_payload,
                success=False,
                message="Store already exists, but bookmarks document was not found for the provided uuid.",
            )

        existing_profile_without_object_id = dict(existing_profile)
        existing_profile_without_object_id.pop("_id", None)
        total_elapsed_ms = (perf_counter() - add_store_started_at) * 1000
        logger.info(
            "[trace_id=%s] Add store request skipped because store id '%s' already exists in %.2f ms.",
            trace_id,
            mapped_profile.id,
            total_elapsed_ms,
        )
        return ResponseBase[Store](
            payload=response_payload,
            success=True,
            message="Store already bookmarked." if bookmark_update_result.modified_count == 0 else "Store was added to bookmarks.",
            data=Store(**existing_profile_without_object_id),
        )

    local_logo_path, logo_download_error = await download_store_logo(
        logo_url=mapped_profile.hd_profile_pic_url,
        store_id=mapped_profile.id,
        trace_id=trace_id,
    )
    if local_logo_path is None:
        total_elapsed_ms = (perf_counter() - add_store_started_at) * 1000
        logger.warning(
            "[trace_id=%s] Add store request failed during logo download for username '%s' in %.2f ms.",
            trace_id,
            page_name,
            total_elapsed_ms,
        )
        return ResponseBase[Store](
            payload=response_payload,
            success=False,
            message=logo_download_error or "Logo image download failed.",
            data=mapped_profile,
        )
    mapped_profile.local_logo_path = local_logo_path

    try:
        insert_result = stores_collection.insert_one(mapped_profile.model_dump())
    except PyMongoError as error:
        total_elapsed_ms = (perf_counter() - add_store_started_at) * 1000
        logger.warning(
            "[trace_id=%s] Add store request failed during database insert for username '%s' in %.2f ms.",
            trace_id,
            page_name,
            total_elapsed_ms,
        )
        return ResponseBase[Store](
            payload=response_payload,
            success=False,
            message=f"Instagram store lookup succeeded, but persisting profile data to database failed. {str(error) or 'Please try again later.'}",
            data=mapped_profile,
        )

    bookmarks_collection = mongo_db[CollectionName.BOOKMARKS.value]
    bookmark_update_result = bookmarks_collection.update_one(
        {"uuid": bookmarks_uuid},
        {"$addToSet": {"store_ids": insert_result.inserted_id}},
    )
    if bookmark_update_result.matched_count == 0:
        total_elapsed_ms = (perf_counter() - add_store_started_at) * 1000
        logger.warning(
            "[trace_id=%s] Add store request failed: bookmarks not found for uuid '%s' in %.2f ms.",
            trace_id,
            bookmarks_uuid,
            total_elapsed_ms,
        )
        return ResponseBase[Store](
            payload=response_payload,
            success=False,
            message="Store profile was saved, but bookmarks document was not found for the provided uuid.",
            data=mapped_profile,
        )

    background_tasks.add_task(store_info_generation_task, app.state.gemini_client, page_name)

    total_elapsed_ms = (perf_counter() - add_store_started_at) * 1000
    logger.info(
        "[trace_id=%s] Add store request completed successfully for username '%s' in %.2f ms.",
        trace_id,
        page_name,
        total_elapsed_ms,
    )
    return ResponseBase[Store](
        payload=response_payload,
        success=True,
        message="Store profile added and bookmarked successfully.",
        data=mapped_profile,
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
        logger=logger,
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

# testing operations
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