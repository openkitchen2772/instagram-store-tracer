from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ResponseBase(BaseModel, Generic[T]):
    payload: dict[str, str]
    success: bool
    message: str
    data: T | list[T] | None = None
