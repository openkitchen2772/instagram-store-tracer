from pydantic import BaseModel


class StoreDTO(BaseModel):
    id: str
    name: str
    imageUrl: str
    latitude: float
    longitude: float
