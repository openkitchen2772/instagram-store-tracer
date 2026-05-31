import pydantic
import logging
import json
from typing import TypeVar
from google import genai
from google.genai import types

from ai.providers.base import AIServiceClient

T = TypeVar('T', bound=pydantic.BaseModel)

class GeminiClientConfig(pydantic.BaseModel):
    api_key: str
    model: str

class GeminiService(AIServiceClient):
    _client: genai.Client
    _model: str
    _logger: logging.Logger

    def __init__(self, config: GeminiClientConfig, logger: logging.Logger):
        logger.info(f"Initiating gemini api client (model: '{config.model}')")
        self._logger = logger
        self._model = config.model
        self._client = genai.Client(
            vertexai=True,
            api_key=config.api_key
        )

    def generate_text(self, prompt: str) -> str:
        try:
            self._logger.info(f"Using model '{self._model}' for google search and generate text response...")
            response = self._client.models.generate_content(
                model=self._model,
                contents=prompt
            )
            self._logger.info("\n--- Gemini response text begins ---")
            self._logger.info(response.text)
            self._logger.info("\n--- Gemini response text ends ---")
            
            return response.text
        except Exception as e:
            self._logger.info(f"Gemini API generates text response failed - {e}")
            raise

    def generate_structured(self, prompt: str, schema: type[T]) -> T:
        try:
            self._logger.info(f"Using model '{self._model}' for google search and generate schema response...")

            response = self._client.models.generate_content(
                model=self._model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    tools=[types.Tool(google_search=types.GoogleSearch())],
                    response_mime_type="application/json",
                    response_schema=schema,
                    temperature=0.0
                )
            )
            self._logger.info("\n--- Gemini response text begins ---")
            self._logger.info(response.text)
            self._logger.info("\n--- Gemini response text ends ---")
            
            return schema.model_validate_json(response.text)
        except Exception as e:
            self._logger.info(f"Gemini API generates structured response failed - {e}")
            raise
