from starlette_admin.contrib.sqla import ModelView

from src.core.models import CountryModel


class CountryAdminView(ModelView):
    """Админка для отображения стран"""

    model = CountryModel
    label = "Страны"

    fields = ["id", "name", "name_eng", "iso_alpha_2", "iso_alpha_3", "is_active"]
    list_display = ["id", "name", "name_eng", "population", "is_active"]  # Какие поля рисуем для list

    sortable_fields = [
        "id",
        "name",
        "name_eng",
        "iso_alpha_2",
        "iso_alpha_3",
        "iso_digits",
        "population",
    ]  # Поля, по которым ищем
    searchable_fields = ["name", "name_eng", "iso_alpha_2", "iso_alpha_3", "iso_digits"]  # Поля для сортировки
    fields_default_sort = [("name", False)]  # Как сортируем по умолчанию

    # Поля, которые исключаем
    exclude_fields_from_detail = ["created_at", "updated_at"]
    exclude_fields_from_list = ["description"]
    exclude_fields_from_edit = ["id", "name", "name_eng", "iso_alpha_2", "iso_alpha_3", "iso_digits", "geometry"]

    # Пагинация
    page_size = 50
    page_size_options = [25, 50, 100]

    # Включение/отключение функционала
    column_visibility = True  # Расширение видимости столбцов
    search_builder = True  # Расширение для построения поиска
    responsive_table = True  # Включение/отключение адаптивного расширения
    save_state = True  # Включение/отключение сохранения состояния
