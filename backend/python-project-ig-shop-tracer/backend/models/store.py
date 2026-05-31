from typing import Any

from pydantic import BaseModel, Field


class Store(BaseModel):
    id: str = ""
    username: str = ""
    full_name: str = ""
    biography: str = ""
    description: str = ""
    tags: list[str] = Field(default_factory=list)
    store_locations: list[tuple[float, float]] = Field(default_factory=list)
    addresses: list[str] = Field(default_factory=list)
    hd_profile_pic_url: str = ""
    contact_phone_number: str = ""
    public_email: str = ""
    city_name: str = ""
    latitude: Any = ""
    longitude: Any = ""
    local_logo_path: str = ""

    def update_from_source_profile(self, source_profile: dict[str, Any]) -> None:
        hd_profile_pic_url_info = source_profile.get("hd_profile_pic_url_info")
        hd_profile_pic_url = ""
        if isinstance(hd_profile_pic_url_info, dict):
            hd_profile_pic_url = str(hd_profile_pic_url_info.get("url", ""))

        self.id = str(source_profile.get("id", "") or "")
        self.username = str(source_profile.get("username", "") or "")
        self.full_name = str(source_profile.get("full_name", "") or "")
        self.biography = str(source_profile.get("biography", "") or "")
        self.hd_profile_pic_url = hd_profile_pic_url
        self.contact_phone_number = str(source_profile.get("contact_phone_number", "") or "")
        self.public_email = str(source_profile.get("public_email", "") or "")
        self.city_name = str(source_profile.get("city_name", "") or "")
        self.latitude = source_profile.get("latitude", "")
        self.longitude = source_profile.get("longitude", "")
