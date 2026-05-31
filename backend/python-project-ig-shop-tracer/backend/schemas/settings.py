from pydantic import BaseModel


class ClientSettings(BaseModel):
    """Public client settings exposed to the front-end."""

    googleMapsApiKey: str = ""
    # Add future front-end settings here, e.g.:
    # featureFlags: dict[str, bool] = {}
