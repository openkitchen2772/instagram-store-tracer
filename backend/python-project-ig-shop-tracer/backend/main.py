import os
import httpx

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# load environmental variable
load_dotenv()  # load env_var for local dev environment, do nothing for prod env
rapid_api_key = os.getenv("RAPIDAPI_KEY")
if rapid_api_key == "":
    raise ValueError("Rapid API Key is missing! Please check if key is set in .env or environmental variables of platform settings.")

app = FastAPI()
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


@app.get("/stores", response_model=list[StoreItemDto])
async def get_store_items(skip: int = 0, limit: int = 0) -> list[StoreItemDto]:
    start_index = max(skip, 0)
    if limit <= 0:
        return STORE_ITEMS[start_index:]
    end_index = start_index + limit
    return STORE_ITEMS[start_index:end_index]


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
