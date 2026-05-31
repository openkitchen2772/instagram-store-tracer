import httpx
from typing import Any

from utils.logger import logger
from config.settings import settings
from time import perf_counter

# RAPID API Settings
INSTAGRAM_RAPID_API: dict[str, dict[str, str]] = {
    "post_user_info": {
        "url": "https://instagram120.p.rapidapi.com/api/instagram/userInfo"
    }
}
INSTAGRAM_RAPID_API_HEADERS: dict[str, str] = {
    "Content-Type": "application/json",
    "x-rapidapi-host": "instagram120.p.rapidapi.com",
    "x-rapidapi-key": settings.RAPID_API_KEY
}
RAPID_API_PROFILE_REQUEST_RETRIES = 3

async def request_rapid_api_profile(page_name: str, trace_id: str | None = None) -> tuple[dict[str, Any] | None, str | None]:
    url = INSTAGRAM_RAPID_API["post_user_info"]["url"]
    headers = INSTAGRAM_RAPID_API_HEADERS
    request_payload = {"username": page_name}
    last_error_message = "Instagram store lookup failed: unknown error."

    # External API can be transiently unavailable; retry a few times before failing.
    for attempt in range(1, RAPID_API_PROFILE_REQUEST_RETRIES + 1):
        logger.info(
            "[trace_id=%s] Rapid API profile request started for username '%s' (attempt %s/%s).",
            trace_id or "n/a",
            page_name,
            attempt,
            RAPID_API_PROFILE_REQUEST_RETRIES,
        )
        request_started_at = perf_counter()
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=request_payload, headers=headers, timeout=20.0)
                response.raise_for_status()
                request_elapsed_ms = (perf_counter() - request_started_at) * 1000
                logger.info(
                    "[trace_id=%s] Rapid API profile request succeeded for username '%s' (attempt %s/%s) with HTTP %s in %.2f ms.",
                    trace_id or "n/a",
                    page_name,
                    attempt,
                    RAPID_API_PROFILE_REQUEST_RETRIES,
                    response.status_code,
                    request_elapsed_ms,
                )
                api_result = response.json()
                if not isinstance(api_result, dict):
                    return None, "Instagram store lookup failed: API returned an unsupported response format."
                return api_result, None
        except httpx.HTTPStatusError as error:
            request_elapsed_ms = (perf_counter() - request_started_at) * 1000
            status_code = error.response.status_code
            logger.warning(
                "[trace_id=%s] Rapid API profile request failed for username '%s' (attempt %s/%s) with HTTP %s in %.2f ms.",
                trace_id or "n/a",
                page_name,
                attempt,
                RAPID_API_PROFILE_REQUEST_RETRIES,
                status_code,
                request_elapsed_ms,
            )
            if status_code < 500 and status_code != 429:
                return None, f"Instagram store lookup failed: external API returned HTTP {status_code}."
            last_error_message = f"Instagram store lookup failed: external API returned HTTP {status_code}."
        except httpx.HTTPError:
            request_elapsed_ms = (perf_counter() - request_started_at) * 1000
            logger.warning(
                "[trace_id=%s] Rapid API profile request network error for username '%s' (attempt %s/%s) after %.2f ms.",
                trace_id or "n/a",
                page_name,
                attempt,
                RAPID_API_PROFILE_REQUEST_RETRIES,
                request_elapsed_ms,
            )
            last_error_message = "Instagram store lookup failed: unable to reach external API."
        except ValueError:
            request_elapsed_ms = (perf_counter() - request_started_at) * 1000
            logger.warning(
                "[trace_id=%s] Rapid API profile request returned invalid JSON for username '%s' (attempt %s/%s) after %.2f ms.",
                trace_id or "n/a",
                page_name,
                attempt,
                RAPID_API_PROFILE_REQUEST_RETRIES,
                request_elapsed_ms,
            )
            return None, "Instagram store lookup failed: API returned invalid JSON."

        if attempt < RAPID_API_PROFILE_REQUEST_RETRIES:
            logger.warning(
                "[trace_id=%s] Rapid API profile request failed on attempt %s/%s for username '%s'. Retrying.",
                trace_id or "n/a",
                attempt,
                RAPID_API_PROFILE_REQUEST_RETRIES,
                page_name,
            )

    return None, f"{last_error_message} Retried {RAPID_API_PROFILE_REQUEST_RETRIES} times."