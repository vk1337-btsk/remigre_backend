from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from src.core.enums import TypeDataEnum


class ShortMetricValueDTO(BaseModel):

    value_numeric: Optional[float] = Field(default=None)
    value_string: Optional[str] = Field(default=None)
    value_boolean: Optional[bool] = Field(default=None)
    value_range_start: Optional[float] = Field(default=None)
    value_range_end: Optional[float] = Field(default=None)
    year: int
    attributes: Dict[str, List[str]]


class ShortMetricInfoDTO(BaseModel):

    id: int
    name: str
    type: TypeDataEnum
    display_priority: int
    values: List[ShortMetricValueDTO]
