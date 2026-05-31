from pydantic import BaseModel, Field

from models.store import Store


class StoreDTO(BaseModel):
    id: str
    objectId: str = ""
    username: str = ""
    fullName: str = ""
    imageUrl: str
    localLogoPath: str = ""
    latitude: float
    longitude: float
    description: str = ""
    tags: list[str] = Field(default_factory=list)
    storeLocations: list[tuple[float, float]] = Field(default_factory=list)
    addresses: list[str] = Field(default_factory=list)

    @classmethod
    def from_store(cls, store: Store, object_id: str = "") -> StoreDTO:
        try:
            latitude = float(store.latitude)
        except (TypeError, ValueError):
            latitude = 0.0

        try:
            longitude = float(store.longitude)
        except (TypeError, ValueError):
            longitude = 0.0

        return cls(
            id=store.id,
            objectId=object_id,
            username=store.username,
            fullName=store.full_name,
            imageUrl=store.hd_profile_pic_url,
            localLogoPath=store.local_logo_path,
            latitude=latitude,
            longitude=longitude,
            description=store.description,
            tags=store.tags,
            storeLocations=store.store_locations,
            addresses=store.addresses,
        )
