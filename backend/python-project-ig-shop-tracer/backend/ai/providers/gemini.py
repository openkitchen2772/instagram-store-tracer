import json
import logging
from typing import Any, TypeVar

import pydantic
from google import genai
from google.genai import types

from ai.providers.base import AIServiceClient

T = TypeVar("T", bound=pydantic.BaseModel)

# Retries when Vertex returns HTTP 200 but no usable text (common with search + JSON schema).
_EMPTY_RESPONSE_MAX_ATTEMPTS = 3

# google-genai HttpOptions.timeout is in milliseconds.
GENERATE_CONTENT_TIMEOUT_MS = 90_000


class GeminiGenerationError(Exception):
    """Raised when Gemini returns no usable content or JSON cannot be parsed."""

    def __init__(self, message: str, *, diagnostics: dict[str, Any] | None = None):
        super().__init__(message)
        self.diagnostics = diagnostics or {}


class GeminiClientConfig(pydantic.BaseModel):
    api_key: str
    model: str


class GeminiService(AIServiceClient):
    _client: genai.Client
    _model: str
    _logger: logging.Logger

    def __init__(self, config: GeminiClientConfig, logger: logging.Logger):
        logger.info("Initiating gemini api client (model: '%s')", config.model)
        self._logger = logger
        self._model = config.model
        self._client = genai.Client(vertexai=True, api_key=config.api_key)

    def generate_text(self, prompt: str) -> str:
        try:
            self._logger.info(
                "Using model '%s' for generate text response...",
                self._model,
            )
            response = self._call_generate_content(
                prompt=prompt,
                config=None,
                label="generate_text",
            )
            text = self._require_response_text(response, context="generate_text")
            self._log_response_text(text, label="generate_text")
            return text
        except GeminiGenerationError:
            raise
        except Exception as error:
            self._logger.warning("Gemini generate_text failed: %s", error)
            raise GeminiGenerationError(f"Gemini generate_text failed: {error}") from error

    def generate_structured(self, prompt: str, schema: type[T]) -> T:
        try:
            self._logger.info(
                "Using model '%s' for google search + structured schema response...",
                self._model,
            )

            last_error: GeminiGenerationError | None = None
            for attempt in range(1, _EMPTY_RESPONSE_MAX_ATTEMPTS + 1):
                label = f"structured_search_attempt_{attempt}"
                try:
                    return self._generate_structured_once(
                        prompt,
                        schema,
                        use_google_search=True,
                        label=label,
                    )
                except GeminiGenerationError as error:
                    last_error = error
                    self._logger.warning(
                        "Gemini structured+search attempt %s/%s failed: %s",
                        attempt,
                        _EMPTY_RESPONSE_MAX_ATTEMPTS,
                        error,
                    )

            if last_error is not None:
                raise GeminiGenerationError(
                    "Gemini structured generation failed after "
                    f"{_EMPTY_RESPONSE_MAX_ATTEMPTS} attempts. Last error: {last_error}",
                    diagnostics=last_error.diagnostics,
                ) from last_error
            raise GeminiGenerationError(
                f"Gemini structured generation failed after {_EMPTY_RESPONSE_MAX_ATTEMPTS} attempts.",
            )
        except GeminiGenerationError:
            raise
        except Exception as error:
            self._logger.warning("Gemini generate_structured failed: %s", error)
            raise GeminiGenerationError(
                f"Gemini generate_structured failed: {error}",
            ) from error

    def _log_response_diagnostics(
        self,
        response: types.GenerateContentResponse,
        *,
        label: str,
        level: int = logging.INFO,
    ) -> None:
        diagnostics = build_response_diagnostics(response)
        self._logger.log(
            level,
            "Gemini response diagnostics [%s]: %s",
            label,
            json.dumps(diagnostics, ensure_ascii=False),
        )

    def _log_response_text(self, text: str | None, *, label: str) -> None:
        self._logger.info("--- Gemini response text begins [%s] ---", label)
        self._logger.info(text if text is not None else "<empty>")
        self._logger.info("--- Gemini response text ends [%s] ---", label)

    def _config_with_timeout(
        self,
        config: types.GenerateContentConfig | None,
    ) -> types.GenerateContentConfig:
        """Apply HTTP timeout to every generate_content request."""
        timeout_options = types.HttpOptions(timeout=GENERATE_CONTENT_TIMEOUT_MS)
        if config is None:
            return types.GenerateContentConfig(http_options=timeout_options)
        if config.http_options is None:
            return config.model_copy(update={"http_options": timeout_options})
        return config.model_copy(
            update={
                "http_options": config.http_options.model_copy(
                    update={"timeout": GENERATE_CONTENT_TIMEOUT_MS},
                ),
            },
        )

    def _call_generate_content(
        self,
        *,
        prompt: str,
        config: types.GenerateContentConfig | None,
        label: str,
    ) -> types.GenerateContentResponse:
        self._logger.info(
            "Gemini generate_content [%s] model='%s' prompt_chars=%s timeout_ms=%s",
            label,
            self._model,
            len(prompt),
            GENERATE_CONTENT_TIMEOUT_MS,
        )
        try:
            return self._client.models.generate_content(
                model=self._model,
                contents=prompt,
                config=self._config_with_timeout(config),
            )
        except Exception as error:
            self._logger.warning(
                "Gemini generate_content [%s] request failed: %s",
                label,
                error,
            )
            raise GeminiGenerationError(
                f"Gemini API request failed ({label}): {error}",
            ) from error

    def _require_response_text(
        self,
        response: types.GenerateContentResponse,
        *,
        context: str,
    ) -> str:
        text = extract_response_text(response)
        if text:
            return text

        self._log_response_diagnostics(response, label=context, level=logging.WARNING)
        message = format_generation_failure_message(response, context=context)
        raise GeminiGenerationError(
            message,
            diagnostics=build_response_diagnostics(response),
        )

    def _parse_structured_json(self, text: str, schema: type[T], *, context: str) -> T:
        try:
            return schema.model_validate_json(text)
        except pydantic.ValidationError as error:
            preview = text[:500] if len(text) > 500 else text
            self._logger.warning(
                "Gemini structured JSON validation failed [%s]: %s; preview=%s",
                context,
                error,
                preview,
            )
            raise GeminiGenerationError(
                f"{context}: response was not valid JSON for schema ({error}).",
            ) from error

    def _generate_structured_once(
        self,
        prompt: str,
        schema: type[T],
        *,
        use_google_search: bool,
        label: str,
    ) -> T:
        tools = (
            [types.Tool(google_search=types.GoogleSearch())]
            if use_google_search
            else None
        )
        config = types.GenerateContentConfig(
            tools=tools,
            response_mime_type="application/json",
            response_schema=schema,
            temperature=0.0,
        )
        response = self._call_generate_content(
            prompt=prompt,
            config=config,
            label=label,
        )
        text = self._require_response_text(response, context=label)
        self._log_response_text(text, label=label)
        return self._parse_structured_json(text, schema, context=label)


# get gemini response log helper functions
def _format_safety_ratings(
    ratings: list[types.SafetyRating] | None,
) -> list[dict[str, str | None]]:
    if not ratings:
        return []
    formatted: list[dict[str, str | None]] = []
    for rating in ratings:
        formatted.append(
            {
                "category": str(getattr(rating, "category", None)),
                "probability": str(getattr(rating, "probability", None)),
                "blocked": str(getattr(rating, "blocked", None)),
            }
        )
    return formatted


def _describe_part(part: types.Part) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "has_text": isinstance(part.text, str),
        "text_length": len(part.text) if isinstance(part.text, str) else 0,
        "thought": getattr(part, "thought", None),
        "has_function_call": getattr(part, "function_call", None) is not None,
        "has_executable_code": getattr(part, "executable_code", None) is not None,
    }
    return summary


def build_response_diagnostics(response: types.GenerateContentResponse) -> dict[str, Any]:
    """Collect API metadata useful when `response.text` is empty or blocked."""
    diagnostics: dict[str, Any] = {
        "sdk_text_is_none": response.text is None,
        "sdk_text_length": len(response.text or ""),
        "candidate_count": len(response.candidates or []),
    }

    prompt_feedback = response.prompt_feedback
    if prompt_feedback is not None:
        diagnostics["prompt_feedback"] = {
            "block_reason": str(getattr(prompt_feedback, "block_reason", None)),
            "block_reason_message": getattr(prompt_feedback, "block_reason_message", None),
            "safety_ratings": _format_safety_ratings(
                getattr(prompt_feedback, "safety_ratings", None)
            ),
        }

    usage = response.usage_metadata
    if usage is not None:
        diagnostics["usage_metadata"] = {
            "prompt_token_count": getattr(usage, "prompt_token_count", None),
            "candidates_token_count": getattr(usage, "candidates_token_count", None),
            "total_token_count": getattr(usage, "total_token_count", None),
        }

    candidates_summary: list[dict[str, Any]] = []
    for index, candidate in enumerate(response.candidates or []):
        content = candidate.content
        parts = content.parts if content is not None else None
        part_summaries = [_describe_part(part) for part in (parts or [])]
        candidates_summary.append(
            {
                "index": index,
                "finish_reason": str(getattr(candidate, "finish_reason", None)),
                "finish_message": getattr(candidate, "finish_message", None),
                "part_count": len(parts or []),
                "parts": part_summaries,
                "safety_ratings": _format_safety_ratings(
                    getattr(candidate, "safety_ratings", None)
                ),
                "grounding_chunks": len(
                    getattr(
                        getattr(candidate, "grounding_metadata", None),
                        "grounding_chunks",
                        None,
                    )
                    or []
                ),
            }
        )
    diagnostics["candidates"] = candidates_summary
    return diagnostics


def format_generation_failure_message(
    response: types.GenerateContentResponse,
    *,
    context: str,
) -> str:
    """Human-readable reason when no JSON/text was produced."""
    diagnostics = build_response_diagnostics(response)
    prompt_feedback = diagnostics.get("prompt_feedback") or {}
    block_reason = prompt_feedback.get("block_reason")
    block_message = prompt_feedback.get("block_reason_message")

    if block_reason and str(block_reason) not in ("None", "BLOCKED_REASON_UNSPECIFIED"):
        detail = block_message or block_reason
        return f"{context}: prompt blocked ({detail})."

    candidates = diagnostics.get("candidates") or []
    if not candidates:
        return (
            f"{context}: Gemini returned no candidates "
            "(request may still be processing or was rejected server-side)."
        )

    first = candidates[0]
    finish_reason = first.get("finish_reason")
    finish_message = first.get("finish_message")
    part_count = first.get("part_count", 0)

    if str(finish_reason) not in ("None", "FINISH_REASON_UNSPECIFIED", "STOP"):
        detail = finish_message or finish_reason
        return f"{context}: generation stopped ({detail})."

    if part_count == 0:
        return (
            f"{context}: Gemini returned an empty candidate (0 content parts). "
            "This often happens when Google Search grounding runs but the model "
            "does not emit final JSON; retrying may help."
        )

    if diagnostics.get("sdk_text_length", 0) == 0:
        return (
            f"{context}: response had parts but no extractable text "
            "(e.g. only tool/thought parts)."
        )

    return f"{context}: no usable model output."


def extract_response_text(response: types.GenerateContentResponse) -> str | None:
    """Read text from SDK helper, then fall back to concatenating non-thought parts."""
    sdk_text = response.text
    if isinstance(sdk_text, str) and sdk_text.strip():
        return sdk_text

    if not response.candidates:
        return None

    content = response.candidates[0].content
    if content is None or not content.parts:
        return None

    chunks: list[str] = []
    for part in content.parts:
        if not isinstance(part.text, str) or not part.text:
            continue
        if isinstance(part.thought, bool) and part.thought:
            continue
        chunks.append(part.text)

    combined = "".join(chunks).strip()
    return combined or None

