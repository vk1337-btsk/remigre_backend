import base64
from typing import Any, List

import starlette_admin.fields as admin_fields
from markupsafe import Markup
from sqlalchemy import select, update
from starlette.requests import Request
from starlette_admin import action
from starlette_admin.contrib.sqla import ModelView

from src.core.models import ImageModel


class BinaryImagePreviewField(admin_fields.BaseField):
    def __init__(self, name: str, label: str = "", **kwargs):
        super().__init__(name, label, **kwargs)
        self.attribute = "file_data"

    def render(self, request, value):
        if value:
            encoded = base64.b64encode(value).decode("utf-8")
            return Markup(f'<img src="data:image/png;base64,{encoded}" style="max-width:100px; max-height:100px;">')
        return "-"


class ImageAdminView(ModelView):
    model = ImageModel
    label = "Изображения"

    fields = [
        "id",
        "country",
        "city",
        BinaryImagePreviewField("file_preview", "Превью"),
        "file_name",
        "mime_type",
        "is_main",
        "is_active",
        "caption",
        "sort_order",
    ]
    list_display = [
        "id",
        "country",
        "city",
        BinaryImagePreviewField("file_preview"),
        "file_name",
        "is_main",
        "is_active",
        "caption",
    ]
    searchable_fields = ["file_name", "caption"]
    fields_default_sort = [("id", True)]

    form_fields = {
        "upload": admin_fields.FileField("Загрузить файл", required=False),
    }
    actions = ["set_as_main"]

    async def create(self, request: Request, data: dict) -> Any:

        upload = data.pop("upload", None)
        if upload and hasattr(upload, "file"):
            file_data = await upload.read()
            data["file_data"] = file_data
            data["file_name"] = upload.filename
            data["mime_type"] = upload.content_type
            data["file_path"] = ""

        return await super().create(request, data)

    async def edit(self, request: Request, pk: Any, data: dict) -> Any:

        upload = data.pop("upload", None)
        if upload and hasattr(upload, "file"):
            file_data = await upload.read()
            data["file_data"] = file_data
            data["file_name"] = upload.filename
            data["mime_type"] = upload.content_type
            data["file_path"] = ""

        return await super().edit(request, pk, data)

    @action(
        name="set_as_main",
        text="Сделать главным",
        confirmation="Сделать выбранные изображения главными?",
        submit_btn_text="Да",
        submit_btn_class="btn-success",
    )
    async def set_as_main_action(self, request: Request, pks: List[Any]) -> str:
        session = request.state.sync_sessionmaker()
        async with session.begin():
            for pk in pks:
                result = await session.execute(select(ImageModel).where(ImageModel.id == pk))
                img = result.scalar_one_or_none()
                if img:
                    if img.country_id:
                        await session.execute(
                            update(ImageModel).where(ImageModel.country_id == img.country_id).values(is_main=False)
                        )
                    elif img.city_id:
                        await session.execute(
                            update(ImageModel).where(ImageModel.city_id == img.city_id).values(is_main=False)
                        )
                    img.is_main = True
        return f"{len(pks)} изображений отмечены как главные."
