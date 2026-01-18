from sqladmin import Admin, ModelView

from src.core.database.database import async_engine
from src.ms_main.models.info import InfoModel


class InfoAdminView(ModelView, model=InfoModel):
    column_list = [InfoModel.id, InfoModel.slug, InfoModel.description]
    name = "info"
