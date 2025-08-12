from pydantic import Field
from ms_trava.enum import TypeLocation
from src.core.schemas.base_schemas import BaseSchema


class SearchLocations(BaseSchema):

    id: int = Field(gt=0, title="ID локации")
    name: str = Field(title="Название на русском")
    name_eng: str = Field(title="Название на английском")
    type: TypeLocation = Field(title="Тип локации")
