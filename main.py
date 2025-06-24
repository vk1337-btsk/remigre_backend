# --------------- Запуск логгирования ---------------
import logging

from src.core.config import settings, setup_logging


setup_logging(settings.debug)
logger = logging.getLogger(__name__)


# --------------- Основные импорты ---------------
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from sqladmin import Admin

from src.core.database import async_engine
from src.ms_trava.admin.views import InfoAdminView
from src.ms_trava.routers.info_router import router as info_router
from src.ms_trava.routers.location_router import router as location_router


# --------------- Основное приложение FastAPI ---------------
app = FastAPI(
    title="Trava Zelenee",
    summary="Trava Zelenee",
)


admin = Admin(app, async_engine)
admin.add_view(InfoAdminView)


# --------------- Эндпоинт документации --------------
@app.get("/", summary="Документация (SwaggerUI)", tags=["API Docs"])
def read_root():
    return get_swagger_ui_html(openapi_url="/openapi.json", title="Swagger UI")


# --------------- Подключаем CORS --------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors.allow_origins,
    allow_credentials=settings.cors.allow_credentials,
    allow_methods=settings.cors.allow_methods,
    allow_headers=settings.cors.allow_headers,
)


# --------------- Добавляем маршрутизацию --------------
app.include_router(info_router)
app.include_router(location_router)


# --------------- Логгируем необходимую информацию --------------
logger.info(f"[Trava]: Приложение запущено в режиме {'DEBUG' if settings.debug else 'PROJECT'}")

# --------------- Запуск приложения --------------
if __name__ == "__main__":
    uvicorn.run(app, host=settings.fastapi.host, port=settings.fastapi.port)
