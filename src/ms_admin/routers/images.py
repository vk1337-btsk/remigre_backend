from typing import List

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse

from src.ms_admin.schemas import Responce_ListImages
from src.ms_admin.services.service import ImageService


router = APIRouter(prefix="/images", tags=["Изображения"])


@router.get(
    "/{image_id}",
    summary="Возвращает конкретное изображение по ID (файл)",
)
async def get_image_by_id(
    image_id: int,
    service: ImageService = Depends(),
) -> FileResponse:
    file_path, mime_type = await service.get_image_file(image_id)
    return FileResponse(
        path=file_path,
        media_type=mime_type,
        headers={"Cache-Control": "public, max-age=86400"},
    )


@router.get(
    "/city/{city_id}/main",
    summary="Возвращает главное изображение города",
)
async def get_main_city_image(
    city_id: int,
    service: ImageService = Depends(),
) -> FileResponse:

    file_path, mime_type = await service.get_main_image_file(city_id=city_id)
    return FileResponse(
        path=file_path,
        media_type=mime_type,
        headers={"Cache-Control": "public, max-age=86400"},
    )


@router.get(
    "/country/{country_id}/main",
    summary="Возвращает главное изображение страны (файл)",
)
async def get_main_country_image(
    country_id: int,
    service: ImageService = Depends(),
) -> FileResponse:

    file_path, mime_type = await service.get_main_image_file(country_id=country_id)
    return FileResponse(
        path=file_path,
        media_type=mime_type,
        headers={"Cache-Control": "public, max-age=86400"},
    )


@router.get(
    "/city/{city_id}/images",
    summary="Возвращает список всех изображений города (метаданные + ссылки)",
)
async def get_city_images(
    city_id: int,
    service: ImageService = Depends(),
) -> List[Responce_ListImages]:

    return await service.get_all_images_list(city_id=city_id)


@router.get(
    "/country/{country_id}/images",
    summary="Возвращает список всех изображений страны (метаданные + ссылки)",
)
async def get_country_images(
    country_id: int,
    service: ImageService = Depends(),
) -> List[Responce_ListImages]:

    return await service.get_all_images_list(country_id=country_id)
