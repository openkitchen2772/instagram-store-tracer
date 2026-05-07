from pydantic import BaseModel, Field


class Bookmarks(BaseModel):
    id: str = ""
    uuid: str = ""
    store_ids: list[str] = Field(default_factory=list)
