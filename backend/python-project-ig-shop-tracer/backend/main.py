import os
import logging
import httpx
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any
from urllib.parse import urlparse
from uuid import uuid4

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
from pymongo.collection import Collection
from pydantic import BaseModel
from instagram_store_db_service import insert_store_profile_if_absent

# load environmental variable
load_dotenv()  # load env_var for local dev environment, do nothing for prod env
rapid_api_key = os.getenv("RAPIDAPI_KEY")
if rapid_api_key == "":
    raise ValueError("Rapid API Key is missing! Please check if key is set in .env or environmental variables of platform settings.")

mongo_connection_string = os.getenv("MONGO_DB_CONNECTION_STRING")
if not mongo_connection_string:
    raise ValueError("MongoDB connection string is missing! Please set MONGO_DB_CONNECTION_STRING in .env or environment variables.")

mongo_database_name = os.getenv("MONGO_DB_NAME", "Staging")
mongo_collection_name = os.getenv("MONGO_DB_COLLECTION", "ig_store")
project_root = Path(__file__).resolve().parent.parent
store_logos_folder = project_root / "store_logos"
logs_folder = project_root / "logs"


def setup_logger() -> logging.Logger:
    logs_folder.mkdir(parents=True, exist_ok=True)
    log_file_name = f"{datetime.now().strftime('%Y-%m-%d')}.log"
    log_file_path = logs_folder / log_file_name

    configured_logger = logging.getLogger("instagram_store_tracer")
    configured_logger.setLevel(logging.INFO)
    configured_logger.propagate = False

    if configured_logger.handlers:
        return configured_logger

    log_formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(log_formatter)

    file_handler = logging.FileHandler(log_file_path, encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(log_formatter)

    configured_logger.addHandler(console_handler)
    configured_logger.addHandler(file_handler)
    return configured_logger


logger = setup_logger()


@asynccontextmanager
async def lifespan(application: FastAPI):
    mongo_client = MongoClient(mongo_connection_string, serverSelectionTimeoutMS=5000)
    mongo_db = mongo_client[mongo_database_name]
    stores_collection = mongo_db[mongo_collection_name]

    # Connection check should fail fast on startup if db is not reachable.
    mongo_client.admin.command("ping")
    seeded_count = seed_dummy_store_items_once(stores_collection, mongo_db["seed_meta"])
    print(f"MongoDB connected successfully. Initial seed inserted {seeded_count} record(s).")

    application.state.mongo_client = mongo_client
    application.state.stores_collection = stores_collection
    yield
    mongo_client.close()


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

INSTAGRAM_RAPID_API: dict[str, dict[str, str]] = {
    "post_user_info": {
        "url": "https://instagram120.p.rapidapi.com/api/instagram/userInfo"
    }
}

INSTAGRAM_RAPID_API_HEADERS: dict[str, str] = {
    "Content-Type": "application/json",
    "x-rapidapi-host": "instagram120.p.rapidapi.com",
    "x-rapidapi-key": rapid_api_key
}

RAPID_API_PROFILE_REQUEST_RETRIES = 3


class StoreItemDto(BaseModel):
    id: str
    name: str
    imageUrl: str
    latitude: float
    longitude: float


class InstagramStoreLookupRequest(BaseModel):
    username: str


# Data Interface Models
class StoreProfileDto(BaseModel):
    id: str = ""
    full_name: str = ""
    biography: str = ""
    hd_profile_pic_url: str = ""
    contact_phone_number: str = ""
    public_email: str = ""
    city_name: str = ""
    latitude: Any = ""
    longitude: Any = ""
    local_logo_path: str = ""

    def update_from_source_profile(self, source_profile: dict[str, Any]) -> None:
        hd_profile_pic_url_info = source_profile.get("hd_profile_pic_url_info")
        hd_profile_pic_url = ""
        if isinstance(hd_profile_pic_url_info, dict):
            hd_profile_pic_url = str(hd_profile_pic_url_info.get("url", ""))

        self.id = str(source_profile.get("id", "") or "")
        self.full_name = str(source_profile.get("full_name", "") or "")
        self.biography = str(source_profile.get("biography", "") or "")
        self.hd_profile_pic_url = hd_profile_pic_url
        self.contact_phone_number = str(source_profile.get("contact_phone_number", "") or "")
        self.public_email = str(source_profile.get("public_email", "") or "")
        self.city_name = str(source_profile.get("city_name", "") or "")
        self.latitude = source_profile.get("latitude", "")
        self.longitude = source_profile.get("longitude", "")


class StoreLookupResponseDto(BaseModel):
    payload: dict[str, str]
    success: bool
    message: str
    data: StoreProfileDto | None = None


def to_store_item_dto(profile: StoreProfileDto) -> StoreItemDto:
    latitude_value = profile.latitude
    longitude_value = profile.longitude

    try:
        latitude = float(latitude_value)
    except (TypeError, ValueError):
        latitude = 0.0

    try:
        longitude = float(longitude_value)
    except (TypeError, ValueError):
        longitude = 0.0

    return StoreItemDto(
        id=profile.id,
        name=profile.full_name or profile.id,
        imageUrl=profile.hd_profile_pic_url,
        latitude=latitude,
        longitude=longitude,
    )


def infer_logo_file_extension(image_url: str, content_type: str | None) -> str:
    if content_type:
        content_type_base = content_type.split(";")[0].strip().lower()
        if content_type_base == "image/jpeg":
            return ".jpg"
        if content_type_base == "image/png":
            return ".png"
        if content_type_base == "image/webp":
            return ".webp"
        if content_type_base == "image/gif":
            return ".gif"

    parsed_url = urlparse(image_url)
    url_suffix = Path(parsed_url.path).suffix.strip().lower()
    if url_suffix in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
        return ".jpg" if url_suffix == ".jpeg" else url_suffix
    return ".jpg"


async def download_store_logo(logo_url: str, store_id: str, trace_id: str) -> tuple[str | None, str | None]:
    if logo_url.strip() == "":
        return None, "Store profile did not include a usable picture URL."

    store_logos_folder.mkdir(parents=True, exist_ok=True)
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
        logo_absolute_path = store_logos_folder / logo_filename
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


STORE_ITEMS: list[StoreItemDto] = [
    StoreItemDto(id="s1", name="Store 01", imageUrl="https://picsum.photos/seed/store1/480/480", latitude=40.7128, longitude=-74.006),
    StoreItemDto(id="s2", name="Store 02", imageUrl="https://picsum.photos/seed/store2/480/480", latitude=34.0522, longitude=-118.2437),
    StoreItemDto(id="s3", name="Store 03", imageUrl="https://picsum.photos/seed/store3/480/480", latitude=51.5072, longitude=-0.1276),
    StoreItemDto(id="s4", name="Store 04", imageUrl="https://picsum.photos/seed/store4/480/480", latitude=35.6762, longitude=139.6503),
    StoreItemDto(id="s5", name="Store 05", imageUrl="https://picsum.photos/seed/store5/480/480", latitude=22.3193, longitude=114.1694),
    StoreItemDto(id="s6", name="Store 06", imageUrl="https://picsum.photos/seed/store6/480/480", latitude=1.3521, longitude=103.8198),
    StoreItemDto(id="s7", name="Store 07", imageUrl="https://picsum.photos/seed/store7/480/480", latitude=48.8566, longitude=2.3522),
    StoreItemDto(id="s8", name="Store 08", imageUrl="https://picsum.photos/seed/store8/480/480", latitude=52.52, longitude=13.405),
    StoreItemDto(id="s9", name="Store 09", imageUrl="https://picsum.photos/seed/store9/480/480", latitude=-33.8688, longitude=151.2093),
    StoreItemDto(id="s10", name="Store 10", imageUrl="https://picsum.photos/seed/store10/480/480", latitude=41.9028, longitude=12.4964),
    StoreItemDto(id="s11", name="Store 11", imageUrl="https://picsum.photos/seed/store11/480/480", latitude=37.5665, longitude=126.978),
    StoreItemDto(id="s12", name="Store 12", imageUrl="https://picsum.photos/seed/store12/480/480", latitude=25.033, longitude=121.5654),
]


def seed_dummy_store_items_once(stores_collection: Collection[Any], seed_meta_collection: Collection[Any]) -> int:
    """
    One-time startup seed for local testing.
    Keep this logic isolated so it can be removed quickly later.
    """
    seed_key = "store_items_seed_v1"
    if seed_meta_collection.find_one({"_id": seed_key}) is not None:
        return 0

    inserted_count = 0
    for item in STORE_ITEMS:
        result = stores_collection.update_one(
            {"id": item.id},
            {"$setOnInsert": item.model_dump()},
            upsert=True,
        )
        if result.upserted_id is not None:
            inserted_count += 1

    seed_meta_collection.insert_one(
        {
            "_id": seed_key,
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "insertedCount": inserted_count,
        }
    )
    return inserted_count


@app.get("/stores", response_model=list[StoreItemDto])
async def get_store_items(skip: int = 0, limit: int = 0) -> list[StoreItemDto]:
    start_index = max(skip, 0)
    stores_collection: Collection[Any] = app.state.stores_collection

    cursor = stores_collection.find({}, {"_id": 0})
    cursor = cursor.skip(start_index)
    if limit > 0:
        cursor = cursor.limit(limit)

    records = list(cursor)
    mapped_items: list[StoreItemDto] = []
    for record in records:
        source_record = dict(record)
        source_record.pop("_id", None)
        mapped_items.append(to_store_item_dto(StoreProfileDto(**source_record)))
    return mapped_items


@app.get("/health/db")
async def database_health_check() -> dict[str, str]:
    mongo_client: MongoClient = app.state.mongo_client
    mongo_client.admin.command("ping")
    return {"status": "ok"}


@app.get("/profile/{page_name}")
async def get_page_profile(page_name: str):
    result, _ = await request_rapid_api_profile(page_name)
    return result


async def request_rapid_api_profile(page_name: str, trace_id: str | None = None) -> tuple[dict[str, Any] | None, str | None]:
    url = INSTAGRAM_RAPID_API["post_user_info"]["url"]
    headers = INSTAGRAM_RAPID_API_HEADERS
    request_payload = {"username": page_name}
    last_error_message = "Instagram store lookup failed: unknown error."

    # External API can be transiently unavailable; retry a few times before failing.
    for attempt in range(1, RAPID_API_PROFILE_REQUEST_RETRIES + 1):
        request_started_at = perf_counter()
        logger.info(
            "[trace_id=%s] Rapid API profile request started for username '%s' (attempt %s/%s).",
            trace_id or "n/a",
            page_name,
            attempt,
            RAPID_API_PROFILE_REQUEST_RETRIES,
        )
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=request_payload, headers=headers, timeout=20.0)
                response.raise_for_status()
                request_elapsed_ms = (perf_counter() - request_started_at) * 1000
                logger.info(
                    "[trace_id=%s] Rapid API profile request succeeded for username '%s' (attempt %s/%s) with HTTP %s in %.2f ms.",
                    trace_id or "n/a",
                    page_name,
                    attempt,
                    RAPID_API_PROFILE_REQUEST_RETRIES,
                    response.status_code,
                    request_elapsed_ms,
                )
                api_result = response.json()
                if not isinstance(api_result, dict):
                    return None, "Instagram store lookup failed: API returned an unsupported response format."
                return api_result, None
        except httpx.HTTPStatusError as error:
            request_elapsed_ms = (perf_counter() - request_started_at) * 1000
            status_code = error.response.status_code
            logger.warning(
                "[trace_id=%s] Rapid API profile request failed for username '%s' (attempt %s/%s) with HTTP %s in %.2f ms.",
                trace_id or "n/a",
                page_name,
                attempt,
                RAPID_API_PROFILE_REQUEST_RETRIES,
                status_code,
                request_elapsed_ms,
            )
            if status_code < 500 and status_code != 429:
                return None, f"Instagram store lookup failed: external API returned HTTP {status_code}."
            last_error_message = f"Instagram store lookup failed: external API returned HTTP {status_code}."
        except httpx.HTTPError:
            request_elapsed_ms = (perf_counter() - request_started_at) * 1000
            logger.warning(
                "[trace_id=%s] Rapid API profile request network error for username '%s' (attempt %s/%s) after %.2f ms.",
                trace_id or "n/a",
                page_name,
                attempt,
                RAPID_API_PROFILE_REQUEST_RETRIES,
                request_elapsed_ms,
            )
            last_error_message = "Instagram store lookup failed: unable to reach external API."
        except ValueError:
            request_elapsed_ms = (perf_counter() - request_started_at) * 1000
            logger.warning(
                "[trace_id=%s] Rapid API profile request returned invalid JSON for username '%s' (attempt %s/%s) after %.2f ms.",
                trace_id or "n/a",
                page_name,
                attempt,
                RAPID_API_PROFILE_REQUEST_RETRIES,
                request_elapsed_ms,
            )
            return None, "Instagram store lookup failed: API returned invalid JSON."

        if attempt < RAPID_API_PROFILE_REQUEST_RETRIES:
            logger.warning(
                "[trace_id=%s] Rapid API profile request failed on attempt %s/%s for username '%s'. Retrying.",
                trace_id or "n/a",
                attempt,
                RAPID_API_PROFILE_REQUEST_RETRIES,
                page_name,
            )

    return None, f"{last_error_message} Retried {RAPID_API_PROFILE_REQUEST_RETRIES} times."


@app.post("/add_store")
async def add_store_profile(payload: InstagramStoreLookupRequest) -> StoreLookupResponseDto:
    add_store_started_at = perf_counter()
    trace_id = str(uuid4())
    page_name = payload.username.strip()
    response_payload = {"query_store_name": page_name}
    logger.info("[trace_id=%s] Add store request started for username '%s'.", trace_id, page_name)

    if page_name == "":
        return StoreLookupResponseDto(
            payload=response_payload,
            success=False,
            message="Instagram store lookup rejected: username is required. Provide a valid Instagram username and try again.",
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
        return StoreLookupResponseDto(
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

    mapped_profile = StoreProfileDto()
    mapped_profile.update_from_source_profile(source_profile)

    if mapped_profile.id == "":
        return StoreLookupResponseDto(
            payload=response_payload,
            success=False,
            message="Instagram store lookup completed but no usable profile was found. Verify the username and ensure the account is accessible.",
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
        return StoreLookupResponseDto(
            payload=response_payload,
            success=False,
            message=logo_download_error or "Logo image download failed.",
            data=mapped_profile,
        )
    mapped_profile.local_logo_path = local_logo_path

    stores_collection: Collection[Any] = app.state.stores_collection
    operation_success_message = "Instagram store lookup successful. Profile data was retrieved and mapped for downstream use."
    db_operation_success, db_error_message = insert_store_profile_if_absent(
        stores_collection=stores_collection,
        profile_data=mapped_profile.model_dump(),
        logger=logger,
    )
    if not db_operation_success:
        total_elapsed_ms = (perf_counter() - add_store_started_at) * 1000
        logger.warning(
            "[trace_id=%s] Add store request failed during database insert for username '%s' in %.2f ms.",
            trace_id,
            page_name,
            total_elapsed_ms,
        )
        return StoreLookupResponseDto(
            payload=response_payload,
            success=False,
            message=f"Instagram store lookup succeeded, but persisting profile data to database failed. {db_error_message or 'Please try again later.'}",
            data=mapped_profile,
        )

    total_elapsed_ms = (perf_counter() - add_store_started_at) * 1000
    logger.info(
        "[trace_id=%s] Add store request completed successfully for username '%s' in %.2f ms.",
        trace_id,
        page_name,
        total_elapsed_ms,
    )
    return StoreLookupResponseDto(
        payload=response_payload,
        success=True,
        message=operation_success_message,
        data=mapped_profile,
    )
