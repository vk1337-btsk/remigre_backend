from pydantic import BaseModel, Field


class Responce_UploadImage(BaseModel):

    id: int
    file_path: str


class Responce_ListImages(BaseModel):

    class Config:
        from_attributes = True

    id: int = Field(description="ID изображения")
    url: str = Field(description="URL для получения изображения")
    is_main: bool = Field(description="Статус главного изображения")
    caption: str
    sort_order: int
    mime_type: str
    file_name: str
