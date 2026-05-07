from pydantic import BaseModel


class StoreAdd(BaseModel):
    username: str
