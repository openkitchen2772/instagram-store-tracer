from pydantic import BaseModel

from dtos.store import StoreDTO


class BookmarksDTO(BaseModel):
    uuid: str
    stores: list[StoreDTO]
