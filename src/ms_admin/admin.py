from fastapi import FastAPI
from starlette_admin.auth import AdminUser, AuthProvider
from starlette_admin.contrib.sqla import Admin
from starlette_admin.exceptions import LoginFailed
from starlette_admin.views import Link

from src.core.models import CityModel, CountryModel, ImageModel
from src.ms_admin.views import (
    CityAdminView,
    CountryAdminView,
    ImageAdminView,
    LocationAnalyticsView,
    MetricAnalyticsView,
)
from src.core.config import settings


class SimpleAuthProvider(AuthProvider):
    """Простой провайдер аутентификации для админки."""

    async def login(self, username: str, password: str, remember_me: bool) -> AdminUser:
        """Проверка логина и пароля."""

        admin_user = settings.project.docs_username
        admin_pass = settings.project.docs_password

        if username == admin_user and password == admin_pass:
            return AdminUser(username=username)

        raise LoginFailed("Неверные учетные данные")

    async def is_authenticated(self, request) -> bool:
        """Проверка, авторизован ли пользователь."""
        user = request.session.get("user")
        return user is not None

    async def logout(self, request) -> bool:
        """Выход из системы."""
        request.session.pop("user", None)
        return True


def setup_admin(app: FastAPI):

    admin = Admin(
        engine=app.state.async_engine,
        title="Админка",
        base_url="/admin",
        templates_dir="src/ms_admin/templates",
        debug=True,
        auth_provider=SimpleAuthProvider(),
    )

    admin.add_view(Link(label="Документация", icon="fa fa-link", url="/"))

    admin.add_view(CountryAdminView(model=CountryModel))
    admin.add_view(CityAdminView(model=CityModel))
    admin.add_view(ImageAdminView(model=ImageModel))

    admin.add_view(MetricAnalyticsView(label="Аналитика метрик", path="/analytic"))
    admin.add_view(LocationAnalyticsView(label="Аналитика стран/городов", path="/location-analytic"))  # добавили

    admin.mount_to(app)
