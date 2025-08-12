from src.core.schemas.base_schemas import BaseSchema


class CountryOnlyListSchema(BaseSchema):

    id: int
    name: str
