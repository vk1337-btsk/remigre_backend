from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from src.ms_admin.schemas import Responce_UploadImage
from src.ms_admin.services.service import ImageService


router = APIRouter(prefix="/admin", tags=["Админка"])


@router.post(
    "/image/upload",
    summary="Сохраняет в БД картинку для страны или города по её ID",
)
async def upload_country_image(
    file: UploadFile = File(...),
    is_main: bool = Form(False),
    caption: str = Form(None),
    sort_order: int = Form(0),
    type: Literal["city", "country"] = Form(None),
    object_id: int = Form(),
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
