from typing import List, Optional, Sequence

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.models import ImageModel


class DB_ImageService:

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_image(
        self,
        city_id: Optional[int],
        country_id: Optional[int],
        file_data: bytes,
        file_path: str,
        file_name: str,
        mime_type: Optional[str],
        is_main: bool,
        caption: Optional[str],
        sort_order: int,
    ) -> ImageModel:
        """Создаёт запись изображения, при необходимости сбрасывает флаг is_main
        у других изображений той же сущности. Возвращает созданный объект
        """

        image = ImageModel(
            city_id=city_id,
            country_id=country_id,
            file_data=file_data,
            file_path=file_path,
            file_name=file_name,
            mime_type=mime_type,
            is_main=is_main,
            caption=caption,
            sort_order=sort_order,
        )
        self.session.add(image)
        await self.session.flush()  # получаем ID

        # Если это главное фото, сбрасываем флаг у других изображений
        if is_main:
            if city_id is not None:
                stmt = (
                    update(ImageModel)
                    .where(ImageModel.city_id == city_id, ImageModel.is_main == True, ImageModel.id != image.id)
                    .values(is_main=False)
                )
                await self.session.execute(stmt)
            else:
                stmt = (
                    update(ImageModel)
                    .where(ImageModel.country_id == country_id, ImageModel.is_main == True, ImageModel.id != image.id)
                    .values(is_main=False)
                )
                await self.session.execute(stmt)

        # Фиксируем транзакцию и обновляем объект
        await self.session.commit()
        await self.session.refresh(image)

        return image

    async def get_image_by_id(self, image_id: int) -> Optional[ImageModel]:
        """Получает изображение по ID"""

        stmt = select(ImageModel).where(ImageModel.id == image_id, ImageModel.is_active == True)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_main_city_image(self, city_id: int) -> Optional[ImageModel]:
        stmt = (
            select(ImageModel)
            .where(ImageModel.city_id == city_id, ImageModel.is_active == True, ImageModel.is_main == True)
            .order_by(ImageModel.sort_order)
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_main_country_image(self, country_id: int) -> Optional[ImageModel]:
        stmt = (
            select(ImageModel)
            .where(ImageModel.country_id == country_id, ImageModel.is_active == True, ImageModel.is_main == True)
            .order_by(ImageModel.sort_order)
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all_images(
        self, city_id: Optional[int] = None, country_id: Optional[int] = None
    ) -> Sequence[ImageModel]:

        if city_id is not None:
            stmt = (
                select(ImageModel)
                .where(ImageModel.city_id == city_id, ImageModel.is_active == True)
                .order_by(ImageModel.sort_order)
            )
        elif country_id is not None:
            stmt = (
                select(ImageModel)
                .where(ImageModel.country_id == country_id, ImageModel.is_active == True)
                .order_by(ImageModel.sort_order)
            )
        else:
            raise ValueError("Нужно передать либо city_id, либо country_id")

        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_country_images(self, country_id: int) -> Sequence[ImageModel]:
        stmt = (
            select(ImageModel)
            .where(ImageModel.country_id == country_id, ImageModel.is_active == True)
            .order_by(ImageModel.sort_order)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
