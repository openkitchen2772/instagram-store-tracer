import pydantic
from ai.providers.base import AIServiceClient


class StoreSearch(pydantic.BaseModel):
    username: str = pydantic.Field(
        description="此 IG 商店的帳號 Username（不含 @）。",
    )
    description: str = pydantic.Field(
        description="一段文字，描述此 IG 商鋪及其業務與商品。",
    )
    tags: list[str] = pydantic.Field(
        description=(
            "此 IG 商店的標籤陣列，供搜索與分類使用。"
            "範例：['麵包店','旺角','銅鑼灣','連鎖餐飲','連鎖零售','珍珠奶茶',"
            "'本地品牌','手工麵包','酸種麵包','港式']"
        ),
    )
    addresses: list[str] = pydantic.Field(
        description=(
            "列出此 IG 商店在香港所有分店的文字地址陣列。"
            "請先從 Instagram, Facebook, Threads店鋪頁面或其官方網站整理現有分店地址；"
            "請透過從Openrice,Instagram專頁以及Facebook專頁搜索商鋪名稱, 確認地址是否已搬遷或者結業，如果已搬遷結業就不要列出；"
            "如果搜索後懷疑為已結業或搬遷的地址，則在地址尾端附上'(或已結業)'。"
        ),
    )
    google_places_search_prompt: str = pydantic.Field(
        description=(
            "用於 Google Places API 搜索香港分店的提示詞。"
            "請根據 Instagram 商鋪各分店地址(先整理出地址)，透過業務類型, 以及列出所有其分店全寫地址的來填寫。"
            "範例：'香港 意式雪糕 康城 旺角 觀塘 屯門 荔枝角 沙田 葵芳 銅鑼灣 GANTO GELATO'"
        ),
    )


class StoreAIService:
    _client: AIServiceClient

    def __init__(self, client: AIServiceClient):
        self._client = client

    def generate(self, username: str) -> StoreSearch:
        normalized_username = username.strip().lstrip("@")
        prompt = (
            f"請搜索香港 Instagram 商店 @{normalized_username} 的公開資料，"
            f"並根據 schema 填寫結果。username 必須是 {normalized_username}。"
            f"請準確填寫 addresses 與 google_places_search_prompt；"
            f"地圖經緯度將由 Google Places 另行搜索。"
            f" Instagram: https://www.instagram.com/{normalized_username}/"
        )
        result = self._client.generate_structured(prompt, StoreSearch)
        # Keep caller username authoritative even if the model drifts.
        return result.model_copy(update={"username": normalized_username})
