from sqladmin import Admin, ModelView

from src.core.database import async_engine
from src.core.models import InfoModel


class InfoAdminView(ModelView, model=InfoModel):
    column_list = [InfoModel.id, InfoModel.slug, InfoModel.description]
    name = "info"
