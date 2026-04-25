import os
import httpx
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
from pymongo.collection import Collection
from pydantic import BaseModel

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


class StoreItemDto(BaseModel):
    id: str
    name: str
    imageUrl: str
    latitude: float
    longitude: float


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
    return [StoreItemDto(**record) for record in records]


@app.get("/health/db")
async def database_health_check() -> dict[str, str]:
    mongo_client: MongoClient = app.state.mongo_client
    mongo_client.admin.command("ping")
    return {"status": "ok"}


@app.get("/profile/{page_name}")
async def get_page_profile(page_name: str):
    url = INSTAGRAM_RAPID_API["post_user_info"]["url"]
    headers = INSTAGRAM_RAPID_API_HEADERS
    payloads = {
        "username": page_name
    }

    result = {}
    client: httpx.AsyncClient
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payloads, headers=headers)
        result = response.json()
    return result
