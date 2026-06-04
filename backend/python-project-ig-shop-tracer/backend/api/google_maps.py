import logging
from typing import Any

import pydantic
import requests

from utils.logger import logger

_GEOCODE_API_URL = "https://maps.googleapis.com/maps/api/geocode/json"
_GEOCODE_REQUEST_TIMEOUT_SECONDS = 15

# Match frontend `hongKongBounds.ts` for map marker filtering.
_HONG_KONG_MIN_LATITUDE = 22.153
_HONG_KONG_MAX_LATITUDE = 22.561
_HONG_KONG_MIN_LONGITUDE = 113.826
_HONG_KONG_MAX_LONGITUDE = 114.434


class GoogleMapsGeocodingClientConfig(pydantic.BaseModel):
    api_key: str


def is_within_hong_kong(latitude: float, longitude: float) -> bool:
    return (
        _HONG_KONG_MIN_LATITUDE <= latitude <= _HONG_KONG_MAX_LATITUDE
        and _HONG_KONG_MIN_LONGITUDE <= longitude <= _HONG_KONG_MAX_LONGITUDE
    )


def normalize_address_for_geocoding(address: str) -> str:
    """Bias Geocoding API toward Hong Kong branch addresses."""
    trimmed = address.strip()
    if trimmed == "":
        return ""
    lower = trimmed.casefold()
    if "hong kong" in lower or "香港" in trimmed or ", hk" in lower or lower.endswith(" hk"):
        return trimmed
    return f"{trimmed}, Hong Kong"


class GoogleMapsGeocodingService:
    _api_key: str
    _logger: logging.Logger

    def __init__(self, config: GoogleMapsGeocodingClientConfig, app_logger: logging.Logger = logger):
        app_logger.info("Initiating Google Maps Geocoding API client")
        self._api_key = config.api_key
        self._logger = app_logger

    def geocode_address(self, address: str) -> tuple[float, float] | None:
        """Resolve one address to (latitude, longitude), or None if geocoding fails."""
        query_address = normalize_address_for_geocoding(address)
        if query_address == "":
            return None

        params = {
            "address": query_address,
            "key": self._api_key,
            "region": "hk",
        }
        self._logger.info(
            "Google Maps geocode request started for address '%s'.",
            query_address,
        )

        try:
            response = requests.get(
                _GEOCODE_API_URL,
                params=params,
                timeout=_GEOCODE_REQUEST_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            payload: dict[str, Any] = response.json()
        except requests.RequestException as error:
            self._logger.warning(
                "Google Maps geocode request failed for address '%s': %s",
                query_address,
                error,
            )
            return None

        status = str(payload.get("status", ""))
        if status != "OK":
            self._logger.warning(
                "Google Maps geocode returned status '%s' for address '%s'.",
                status,
                query_address,
            )
            return None

        results = payload.get("results")
        if not isinstance(results, list) or len(results) == 0:
            self._logger.warning(
                "Google Maps geocode returned no results for address '%s'.",
                query_address,
            )
            return None

        first_result = results[0]
        if not isinstance(first_result, dict):
            return None

        geometry = first_result.get("geometry")
        if not isinstance(geometry, dict):
            return None

        location = geometry.get("location")
        if not isinstance(location, dict):
            return None

        latitude = location.get("lat")
        longitude = location.get("lng")
        if not isinstance(latitude, (int, float)) or not isinstance(longitude, (int, float)):
            return None

        lat = float(latitude)
        lng = float(longitude)
        if not is_within_hong_kong(lat, lng):
            self._logger.warning(
                "Google Maps geocode result for '%s' is outside Hong Kong bounds: lat=%s lng=%s.",
                query_address,
                lat,
                lng,
            )
            return None

        self._logger.info(
            "Google Maps geocode succeeded for address '%s' -> lat=%s lng=%s.",
            query_address,
            lat,
            lng,
        )
        return lat, lng

    def geocode_addresses(self, addresses: list[str]) -> list[tuple[float, float]]:
        """Geocode each non-empty address; skips failures and preserves successful order."""
        store_locations: list[tuple[float, float]] = []
        for address in addresses:
            coordinates = self.geocode_address(address)
            if coordinates is not None:
                store_locations.append(coordinates)
        self._logger.info(
            "Google Maps geocode batch completed: %s/%s addresses resolved.",
            len(store_locations),
            len(addresses),
        )
        return store_locations
