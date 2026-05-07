from pydantic import BaseModel


class BookmarksAdd(BaseModel):
    uuid: str
