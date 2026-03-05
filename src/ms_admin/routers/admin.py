from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from src.ms_admin.schemas import Responce_UploadImage
from src.ms_admin.services.service import ImageService


router = APIRouter(prefix="/admin", tags=["Админка"])


@router.post(
    "/image/upload",
    summary="Сохраняет в БД картинку для страны или города по её ID",
    description="Использовать только для загрузки картинок в БД для сайта"
    "\nTODO: добавить потом отдельную авторизацию по X-Api-Key для защиты",
)
async def upload_country_image(
    file: UploadFile = File(description="Файл-картинка для сайта (под капотом валидация под нужные форматы)"),
    is_main: bool = Form(default=False, description="Флаг, означающий статус главной картинки для страны/города"),
    caption: str = Form(default=None, description="Подпись для картинки для страны/города"),
    sort_order: int = Form(default=0, description="Значение для для сортировки картинок"),
    type: Literal["city", "country"] = Form(
        default=None, description="Тип картинки (для страны или для города). Указывать или 'city', или 'country'"
    ),
    object_id: int = Form(description="ID к которому привязать картинку (на текущем этапе или к городу, или к стране"),
    service: ImageService = Depends(),
) -> Responce_UploadImage:

    if type == "city":
        return await service.save_image(
            file=file, city_id=object_id, is_main=is_main, caption=caption, sort_order=sort_order
        )
    elif type == "country":
        return await service.save_image(
            file=file, country_id=object_id, is_main=is_main, caption=caption, sort_order=sort_order
        )
    else:
        raise HTTPException(status_code=400, detail="Неизвестный тип объекта")
