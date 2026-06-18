from typing import Generic, Optional, TypeVar, Dict, Any, List
from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


# ---------------------------------------------------------
# STANDARD ERROR RESPONSE
# ---------------------------------------------------------
class ErrorResponse(BaseModel):
    ok: bool = False
    error: Any  # can be string or dict

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------
# STANDARD SUCCESS RESPONSE (Generic)
# ---------------------------------------------------------
class StandardResponse(BaseModel, Generic[T]):
    ok: bool = True
    message: Optional[str] = None
    data: Optional[T] = None

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------
# SIMPLE SUCCESS RESPONSE
# ---------------------------------------------------------
class SuccessResponse(BaseModel):
    ok: bool = True
    message: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------
# PAGINATION MODELS
# ---------------------------------------------------------
class Pagination(BaseModel):
    page: int
    page_size: int
    total: int

    model_config = ConfigDict(from_attributes=True)


class PaginatedResponse(BaseModel, Generic[T]):
    ok: bool = True
    data: List[T]
    pagination: Pagination

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------
# SCORECARD MODEL (Used for AI scoring)
# ---------------------------------------------------------
class ScoreCard(BaseModel):
    communication: int
    appearance: int
    attitude: int
    behaviour: int
    confidence: int
    total: int

    model_config = ConfigDict(from_attributes=True)
