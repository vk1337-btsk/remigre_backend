from starlette_admin.contrib.sqla import ModelView

from src.core.models import CityModel


class CityAdminView(ModelView):
    """Админка для отображения городов"""

    model = CityModel
    label = "Города"

    fields = ["id", "country_id", "country", "name", "name_eng", "is_capital", "is_active", "population"]
    list_display = ["id", "name", "name_eng", "is_active", "description"]

    searchable_fields = ["name", "name_eng"]

    fields_default_sort = [("name", False)]

    # Поля, которые исключаем
    exclude_fields_from_detail = ["created_at", "updated_at"]
    exclude_fields_from_list = ["description"]
    exclude_fields_from_edit = ["id", "name", "name_eng", "iso_alpha_2", "iso_alpha_3", "iso_digits", "geometry"]
    # exclude_fields_from_create = []

    # Пагинация
    page_size = 50
    page_size_options = [25, 50, 100]

    # Включение/отключение функционала
    column_visibility = True  # Расширение видимости столбцов
    search_builder = True  # Расширение для построения поиска
    responsive_table = True  # Включение/отключение адаптивного расширения
    save_state = True  # Включение/отключение сохранения состояния
