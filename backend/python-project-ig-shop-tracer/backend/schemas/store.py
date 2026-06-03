from pydantic import BaseModel


class StoreAdd(BaseModel):
    username: str
    uuid: str


class StoreRenew(BaseModel):
    username: str


class StoreDelete(BaseModel):
    uuid: str
    store_id: str


class StoreAIGenerate(BaseModel):
    username: str
