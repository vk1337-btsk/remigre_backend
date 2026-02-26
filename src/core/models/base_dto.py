import logging
from typing import Any, Optional

from pydantic import BaseModel, Field


logger = logging.getLogger(__name__)


class GetFilteredListDTO(BaseModel):

    filters: Optional[dict[str, Any]] = None
    like_filters: Optional[dict[str, str]] = None
    or_like_filters: Optional[dict[str, str]] = None
    in_filters: Optional[dict[str, list[Any]]] = None
    limit: Optional[int] = Field(default=None, ge=1, le=1000, description="Максимум 1000 записей")
    offset: Optional[int] = Field(default=0, ge=0, description="Смещение для пагинации")
    sort_by: Optional[str] = None
    sort_desc: Optional[bool] = False
