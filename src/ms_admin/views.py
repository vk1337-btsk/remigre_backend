from sqladmin import ModelView

from src.core.models.locations.country import CountryModel


class CountryAdmin(ModelView, model=CountryModel):
    column_list = [CountryModel.id, CountryModel.name]
