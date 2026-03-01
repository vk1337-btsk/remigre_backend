from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from src.core.enums import TypeDataEnum
from src.core.schemas.base_schemas import BaseSchema


class LocationMainInfoSchema(BaseSchema):
    """Список стран/городов"""

    id: int = Field(description="ID объекта локации")
    type: Literal["country", "city"] = Field(description="Тип объекта локации (страна или город)")
    name: str = Field(description="Название объекта локации (на русском)")
    iso_code: str = Field(description="ISO-code alpha 2 страны объекта локации")


# ============ Схемы для стран ============
class MetricValueSchema(BaseModel):
    """Схема значения метрики"""

    value: Any = Field(title="Значение метрики")
    year: int = Field(title="Год значения метрики")
    priority: int = Field(title="Приоритет отображения метрики (не уверен, что он нужен)")
    attributes: Dict[str, str] = Field(title="Атрибуты метрики, такие как: пол, валюта, образование и т.д.")


class MetricInfoSchema(BaseModel):
    """Схема метрики"""

    id: int = Field(description="ID метрики")
    name: str = Field(description="Название метрики")
    type: TypeDataEnum = Field(description="Тип данных метрики")
    values: List[MetricValueSchema] = Field(description="Список значений в зависимости от года и атрибутов")


class CountryShortInfoDetail(BaseModel):
    """Краткая информация о стране с характеристиками и метриками"""

    id: int = Field(description="ID страны")
    name: str = Field(description="Название страны")
    iso_alpha_2: str = Field(description="Код ISO (2-х буквенный)")
    population: Optional[int] = Field(default=None, description="Население страны")
    metrics: List[MetricInfoSchema] = Field(default_factory=list, description="Список с основными метриками страны")


class ListPaginatedCountryShortInfo(BaseModel):
    """Схема возврата списка стран с краткой характеристикой и основными метриками"""

    total: int = Field(default=0, description="Общее кол-во стран")
    items: List[CountryShortInfoDetail] = Field(
        default_factory=list, description="Список стран с характеристиками и метриками"
    )
