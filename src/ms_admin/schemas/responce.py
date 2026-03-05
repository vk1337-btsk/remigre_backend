from pydantic import BaseModel, Field


class Responce_UploadImage(BaseModel):

    id: int = Field(description="ID изображения")
    file_path: str = Field(description="Путь к изображению")


class Responce_ListImages(BaseModel):

    class Config:
        from_attributes = True

    id: int = Field(description="ID изображения")
    url: str = Field(description="URL для получения изображения")
    is_main: bool = Field(description="Статус главного изображения")
    caption: str = Field(description="Подпись к изображению")
    sort_order: int = Field(description="Значение для сортировки изображения")
    mime_type: str = Field(description="MIME тип изображения")
    file_name: str = Field(description="Название изображения")
