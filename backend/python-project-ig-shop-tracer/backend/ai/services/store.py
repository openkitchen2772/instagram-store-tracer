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
        description="此 IG 商店在香港各分店的文字地址陣列，請優先利用Instagram/Facebook/Threads店鋪頁面裡的資料，或是店鋪官方網站資料，請注意不要加入已結業的地址，再嘗試以網絡資料補充。",
    )
    google_places_search_prompt: str = pydantic.Field(
        description="用於Google Places API做分店地址搜索的提示詞，請根據其instagram商鋪頁面描述，地區以及商鋪類型等給出一組提示詞，範例'香港 連鎖餐廳 港式快餐店 大快活'",
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
            f" Instagram: https://www.instagram.com/{normalized_username}/"
        )
        result = self._client.generate_structured(prompt, StoreSearch)
        # Keep caller username authoritative even if the model drifts.
        return result.model_copy(update={"username": normalized_username})
