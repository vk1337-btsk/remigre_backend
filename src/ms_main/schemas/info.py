from pydantic import Field
from src.core.schemas.base_schemas import BaseSchema


class InfoModelSchema(BaseSchema):

    id: int = Field(title="ID записи")
    slug: str = Field(title="Название раздела")
    description: str = Field(title="Описание раздела")
