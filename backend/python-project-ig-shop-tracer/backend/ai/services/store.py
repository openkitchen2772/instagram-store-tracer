import pydantic
from ai.providers.base import AIServiceClient


class StoreLocation(pydantic.BaseModel):
    """Branch coordinates for Gemini structured output (tuple types are unsupported)."""

    latitude: float = pydantic.Field(description="分店緯度")
    longitude: float = pydantic.Field(description="分店經度")


class StoreSearch(pydantic.BaseModel):
    username: str = pydantic.Field(description="商店IG頁面的Username")
    description: str = pydantic.Field(description="一段對於這個IG商鋪與其業務商品的描述段落")
    tags: list[str] = pydantic.Field(
        description="一個關於這個IG商店的標籤陣列,將會用於商店的搜索和分類之用,例如:['麵包店','旺角','銅鑼灣','連鎖餐飲','連鎖零售','珍珠奶茶','本地品牌','手工麵包','酸種麵包','港式']",
    )
    locations: list[StoreLocation] = pydantic.Field(
        description="這個IG商店的在港各分店的經緯度地點,將用於google maps顯示位置,請透過網絡搜索結果,例如但不限於openrice或是Instagram或是官方網站,取得後請也嘗試以google maps驗證座標是否該店家,例如:[{'latitude':22.0934,'longitude':114.060349},{'latitude':22.443434,'longitude':114.343545}]",
    )
    addresses: list[str] = pydantic.Field(
        description="一個關於此IG商店的香港各分店地址的陣列"
    )

    def location_tuples(self) -> list[tuple[float, float]]:
        return [(location.latitude, location.longitude) for location in self.locations]


class StoreAIService:
    _client: AIServiceClient

    def __init__(self, client: AIServiceClient):
        self._client = client

    def generate(self, username: str) -> StoreSearch:
        prompt = f"請幫我搜索關於@{username}這個IG商店的資料並根據schema填充並返回結果."
        return self._client.generate_structured(prompt, StoreSearch)
