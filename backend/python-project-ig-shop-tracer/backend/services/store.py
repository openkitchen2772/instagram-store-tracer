import logging
import re
import pydantic
import httpx
from typing import Any
from time import perf_counter
from uuid import uuid4

from models.collections import CollectionName
from models.store import Store
from pymongo.errors import PyMongoError
from pymongo.collection import Collection
from services.database import get_mongo_db
from utils.logger import logger
from utils.utility import infer_logo_file_extension
from config.settings import settings
from ai.services.store import StoreAIService
from ai.providers.gemini import GeminiService

# Operation services
async def download_store_logo(logo_url: str, store_id: str, trace_id: str) -> tuple[str | None, str | None]:
    if logo_url.strip() == "":
        return None, "Store profile did not include a usable picture URL."

    store_logos_folder_path = settings.STORE_LOGOS_FOLDER_PATH
    store_logos_folder_path.mkdir(parents=True, exist_ok=True)
    request_started_at = perf_counter()
    try:
        logger.info(
            "[trace_id=%s] Logo download request started for store_id '%s' from url '%s'.",
            trace_id,
            store_id,
            logo_url,
        )
        async with httpx.AsyncClient() as client:
            response = await client.get(logo_url, follow_redirects=True, timeout=20.0)
            response.raise_for_status()
        request_elapsed_ms = (perf_counter() - request_started_at) * 1000
        logger.info(
            "[trace_id=%s] Logo download request finished for store_id '%s' with HTTP %s in %.2f ms.",
            trace_id,
            store_id,
            response.status_code,
            request_elapsed_ms,
        )

        logo_extension = infer_logo_file_extension(logo_url, response.headers.get("content-type"))
        logo_filename = f"{store_id}{logo_extension}"
        logo_absolute_path = store_logos_folder_path / logo_filename
        logo_absolute_path.write_bytes(response.content)
        return f"/store_logos/{logo_filename}", None
    except httpx.HTTPStatusError as error:
        request_elapsed_ms = (perf_counter() - request_started_at) * 1000
        logger.warning(
            "[trace_id=%s] Logo download failed for store_id '%s' with HTTP %s in %.2f ms.",
            trace_id,
            store_id,
            error.response.status_code,
            request_elapsed_ms,
        )
        return None, f"Logo image download failed: endpoint returned HTTP {error.response.status_code}."
    except httpx.HTTPError:
        request_elapsed_ms = (perf_counter() - request_started_at) * 1000
        logger.warning(
            "[trace_id=%s] Logo download network error for store_id '%s' after %.2f ms.",
            trace_id,
            store_id,
            request_elapsed_ms,
        )
        return None, "Logo image download failed: unable to reach picture URL."
    except OSError:
        request_elapsed_ms = (perf_counter() - request_started_at) * 1000
        logger.warning(
            "[trace_id=%s] Logo write failed for store_id '%s' after %.2f ms.",
            trace_id,
            store_id,
            request_elapsed_ms,
        )
        return None, "Logo image download failed: unable to write image file to local storage."

def store_info_generation_task(gemini_client: GeminiService, username: str) -> None:
    """Generate store AI data via Gemini, then upsert results into MongoDB."""
    trace_id = str(uuid4())
    mongo_db = get_mongo_db()
    store_ai_service: StoreAIService = StoreAIService(gemini_client)
    stores_collection: Collection[Any] = mongo_db[CollectionName.STORE.value]
    job_started_at = perf_counter()
    ai_processing_placeholder = "AI is analyzing this store for you..."

    try:
        placeholder_update_result = stores_collection.update_one(
            {"username": username},
            {
                "$set": {
                    "description": ai_processing_placeholder,
                    "addresses": [ai_processing_placeholder],
                }
            },
        )
        logger.info(
            "[trace_id=%s] Store AI background job placeholder update for username '%s' matched=%s modified=%s.",
            trace_id,
            username,
            placeholder_update_result.matched_count,
            placeholder_update_result.modified_count,
        )
    except PyMongoError as error:
        logger.warning(
            "[trace_id=%s] Store AI background job placeholder update failed for username '%s': %s",
            trace_id,
            username,
            error,
        )

    try:
        ai_result = store_ai_service.generate(username)
    except Exception as error:
        total_elapsed_ms = (perf_counter() - job_started_at) * 1000
        logger.warning(
            "[trace_id=%s] Store AI background job failed during Gemini call for username '%s' in %.2f ms: %s",
            trace_id,
            username,
            total_elapsed_ms,
            error,
        )
        return

    saved_store, was_created, error_message, mongo_object_id = upsert_store_from_ai_data(
        username=username,
        description=ai_result.description,
        tags=ai_result.tags,
        store_locations=ai_result.location_tuples(),
        addresses=ai_result.addresses,
        logger=logger,
    )
    if saved_store is None:
        total_elapsed_ms = (perf_counter() - job_started_at) * 1000
        logger.warning(
            "[trace_id=%s] Store AI background job failed during database upsert for username '%s' in %.2f ms: %s",
            trace_id,
            username,
            total_elapsed_ms,
            error_message or "unknown error",
        )
        return

    total_elapsed_ms = (perf_counter() - job_started_at) * 1000
    logger.info(
        "[trace_id=%s] Store AI background job completed for username '%s' (%s, object_id=%s) in %.2f ms.",
        trace_id,
        username,
        "created" if was_created else "updated",
        mongo_object_id,
        total_elapsed_ms,
    )

# Database services
def create_store(
    profile_data: dict[str, Any],
    logger: logging.Logger,
) -> tuple[bool, str | None]:
    profile_id = str(profile_data.get("id", "") or "")
    if profile_id == "":
        return False, "Store profile is missing required id field."

    logger.info("DB operation start: check existing profile for id=%s", profile_id)

    try:
        mongo_db = get_mongo_db()
        stores_collection = mongo_db[CollectionName.STORE.value]
        existing_profile = stores_collection.find_one({"id": profile_id}, {"_id": 1})
        if existing_profile is None:
            logger.info("DB operation: no existing profile found, inserting id=%s", profile_id)
            insert_result = stores_collection.insert_one(profile_data)
            logger.info(
                "DB operation result: insert success for id=%s, inserted_id=%s",
                profile_id,
                insert_result.inserted_id,
            )
        else:
            logger.info("DB operation: profile exists, refreshing document for id=%s", profile_id)
            update_result = stores_collection.update_one(
                {"id": profile_id},
                {"$set": profile_data},
            )
            logger.info(
                "DB operation result: refresh success for id=%s, matched=%s, modified=%s",
                profile_id,
                update_result.matched_count,
                update_result.modified_count,
            )
        return True, None
    except PyMongoError as error:
        logger.error("DB operation failed for id=%s: %s", profile_id, str(error))
        return False, "Database operation failed while saving store profile."


def upsert_store_from_ai_data(
    username: str,
    description: str,
    tags: list[str],
    store_locations: list[tuple[float, float]],
    addresses: list[str],
    logger: logging.Logger,
) -> tuple[Store | None, bool, str | None, str]:
    normalized_username = username.strip().lstrip("@")
    if normalized_username == "":
        return None, False, "Store AI generate rejected: username is required.", ""

    logger.info(
        "DB operation start: AI upsert lookup for username '%s'.",
        normalized_username,
    )

    try:
        mongo_db = get_mongo_db()
        stores_collection = mongo_db[CollectionName.STORE.value]
        username_pattern = f"^{re.escape(normalized_username)}$"
        existing_record = stores_collection.find_one(
            {"username": {"$regex": username_pattern, "$options": "i"}},
        )

        if existing_record is not None:
            existing_store = Store(**dict(existing_record))
            existing_store.description = description
            existing_store.tags = tags
            existing_store.store_locations = store_locations
            existing_store.addresses = addresses

            update_result = stores_collection.update_one(
                {"_id": existing_record["_id"]},
                {"$set": existing_store.model_dump()},
            )
            logger.info(
                "DB operation result: AI upsert updated store username '%s', matched=%s, modified=%s.",
                existing_store.username,
                update_result.matched_count,
                update_result.modified_count,
            )
            return existing_store, False, None, str(existing_record["_id"])

        new_store = Store(
            id=normalized_username,
            username=normalized_username,
            description=description,
            tags=tags,
            store_locations=store_locations,
            addresses=addresses,
        )
        insert_result = stores_collection.insert_one(new_store.model_dump())
        logger.info(
            "DB operation result: AI upsert inserted store username '%s', inserted_id=%s.",
            new_store.username,
            insert_result.inserted_id,
        )
        return new_store, True, None, str(insert_result.inserted_id)
    except PyMongoError as error:
        logger.error(
            "DB operation failed during AI upsert for username '%s': %s",
            normalized_username,
            str(error),
        )
        return None, False, "Database operation failed while saving AI-generated store data.", ""
