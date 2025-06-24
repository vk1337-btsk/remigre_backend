from pydantic import BaseModel, ConfigDict


# --------------- Основная абстрактная схема для отображения ---------------
class BaseSchema(BaseModel):
    """Базовая абстрактная схема"""

    model_config = ConfigDict(from_attributes=True, extra="ignore", use_enum_values=True)
