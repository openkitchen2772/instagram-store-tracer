import pydantic
from typing import TypeVar
from abc import ABC, abstractmethod

T = TypeVar('T', bound=pydantic.BaseModel)

class BaseClient(ABC):
    pass

class AIServiceClient(BaseClient):
    @abstractmethod
    def generate_text(self, prompt: str) -> str:
        pass

    @abstractmethod
    def generate_structured(self, prompt: str, schema_class: type[T]) -> T:
        pass