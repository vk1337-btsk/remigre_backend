import os
import uuid
from pathlib import Path
from typing import List, Optional, cast

import aiofiles
from fastapi import Depends, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.core.dependency import get_async_session, get_sessionmaker
from src.core.models import ImageModel
from src.ms_admin.schemas import Responce_ListImages, Responce_UploadImage
from src.ms_admin.services.db_service import DB_ImageService


UPLOAD_DIR = "uploads"
Path(UPLOAD_DIR).mkdir(exist_ok=True)


class ImageService:

    def __init__(self, session: AsyncSession = Depends(get_async_session)):
        """Инициализация основных параметров."""

        self.service_db = DB_ImageService(session)

    async def save_image(
        self,
        file: UploadFile,
        city_id: Optional[int] = None,
        country_id: Optional[int] = None,
        is_main: bool = False,
        caption: Optional[str] = None,
        sort_order: int = 0,
    ) -> Responce_UploadImage:
        """Сохраняет изображение в БД и на диск (кэш)"""

        # Проверка, что указан ровно один идентификатор
        if (city_id is None) == (country_id is None):
            raise HTTPException(400, "Должен быть указан либо city_id, либо country_id")

        filename = file.filename or "unknown"

        # Генерируем уникальное имя файла и путь к файлу
        file_path = self._generate_file_path(filename)

        # Читаем содержимое файла
        contents = await file.read()

        # Создаём запись в БД и сбрасываем флаг is_main у осатльных изображений, если передан is_main=True
        image = await self.service_db.create_image(
            city_id=city_id,
            country_id=country_id,
            file_data=contents,
            file_path=file_path,
            file_name=filename,
            mime_type=file.content_type,
            is_main=is_main,
            caption=caption,
            sort_order=sort_order,
        )

        # Сохраняем файл на диск (кэш)
        disk_path = os.path.join(UPLOAD_DIR, file_path)
        async with aiofiles.open(disk_path, "wb") as f:
            await f.write(contents)

        return Responce_UploadImage(id=cast(int, image.id), file_path=cast(str, image.file_path))

    async def get_image_file(self, image_id: int) -> tuple[str, str]:
        """Возвращает путь к файлу на диске и MIME-тип по ID."""

        image = await self.service_db.get_image_by_id(image_id)

        if not image:
            raise HTTPException(404, "Изображение не найдено")

        disk_path = await self._ensure_file_on_disk(image)
        mime_type = image.mime_type or "application/octet-stream"

        return disk_path, cast(str, mime_type)

    async def get_main_image_file(
        self, city_id: Optional[int] = None, country_id: Optional[int] = None
    ) -> tuple[str, str]:

        if city_id:
            image = await self._get_main_image("city", city_id)
        elif country_id:
            image = await self._get_main_image("country", country_id)
        else:
            raise HTTPException(status_code=400, detail="Должен быть передан или city_id, или country_id")

        return await self.get_image_file(cast(int, image.id))

    async def get_all_images_list(
        self, city_id: Optional[int] = None, country_id: Optional[int] = None
    ) -> List[Responce_ListImages]:

        if city_id:
            images = await self.service_db.get_all_images(city_id=city_id)
        elif country_id:
            images = await self.service_db.get_all_images(country_id=country_id)
        else:
            raise HTTPException(status_code=400, detail="Должен быть передан или city_id, или country_id")

        return [
            Responce_ListImages(
                id=cast(int, img.id),
                url=f"/images/{img.id}",
                is_main=cast(bool, img.is_main),
                caption=cast(str, img.caption),
                sort_order=cast(int, img.sort_order),
                mime_type=cast(str, img.mime_type),
                file_name=cast(str, img.file_name),
            )
            for img in images
        ]

    async def _get_main_image(self, entity_type: str, entity_id: int) -> ImageModel:
        """Общий метод получения главного изображения."""

        if entity_type == "city":
            image = await self.service_db.get_main_city_image(entity_id)
        elif entity_type == "country":
            image = await self.service_db.get_main_country_image(entity_id)
        else:
            raise HTTPException(400, "Неверный тип сущности")
        if not image:
            raise HTTPException(404, f"Для {entity_type} не найдено изображений")
        return image

    def _generate_file_path(self, original_filename: str) -> str:
        """Общий метод для генерации названия и пути к файлу"""

        ext = os.path.splitext(original_filename)[1].lower()
        if ext not in (".jpg", ".jpeg", ".png", ".gif", ".webp"):
            raise HTTPException(400, "Неподдерживаемый формат файла")
        return f"{uuid.uuid4().hex}{ext}"

    async def _ensure_file_on_disk(self, image: ImageModel) -> str:
        """Гарантирует наличие файла на диске, при необходимости восстанавливает из БД. Возвращает путь к файлу."""

        disk_path = os.path.join(UPLOAD_DIR, cast(str, image.file_path))
        if not os.path.exists(disk_path):
            file_data = cast(bytes, image.file_data)

            if not file_data:
                raise HTTPException(404, "Данные изображения повреждены")

            async with aiofiles.open(disk_path, "wb") as f:
                await f.write(file_data)

        return disk_path
