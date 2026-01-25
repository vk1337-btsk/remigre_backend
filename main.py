# main.py
# --------------- Запуск логгирования ---------------
import logging
from contextlib import asynccontextmanager

from src.core.config import settings, setup_logging
from src.core.dependency import verify_api_key, verify_docs_auth


setup_logging(settings.is_debug)
logger = logging.getLogger(__name__)


# --------------- Основные импорты ---------------
import uvicorn
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.core.utils.ssh_service import start_ssh_tunnel, stop_ssh_tunnel
from src.ms_location.router import router as location_router
from src.ms_main.router import router as info_router
from src.ms_metric.router import router as metric_router


# --------------- Основное приложение FastAPI ---------------
@asynccontextmanager
async def lifespan(app: FastAPI):

    engine = None

    # ---------------- STARTUP ----------------
    try:
        db_host = settings.db.db_host
        db_port = settings.db.db_port

        if not settings.is_project:
            logger.info("[Startup] Local mode → starting SSH tunnel")

            ports = start_ssh_tunnel(
                ssh_host=settings.ssh.host,
                ssh_port=settings.ssh.port,
                ssh_user=settings.ssh.user,
                ssh_key_path=settings.ssh.key_path,
                addresses={
                    "postgresql": ("127.0.0.1", settings.db.db_port),
                },
            )

            db_host = "127.0.0.1"
            db_port = ports["postgresql"]

        logger.info("[Startup] Creating async engine")

        engine = create_async_engine(
            url=(
                f"postgresql+asyncpg://"
                f"{settings.db.db_user}:"
                f"{settings.db.db_password.get_secret_value()}"
                f"@{db_host}:{db_port}/{settings.db.db_name}"
            ),
            echo=settings.db.db_echo,
            pool_pre_ping=True,
            pool_recycle=3600,
        )

        sessionmaker = async_sessionmaker(
            bind=engine,
            expire_on_commit=False,
        )

        app.state.engine = engine
        app.state.sessionmaker = sessionmaker

        # Проверка соединения
        async with engine.connect():
            pass

        logger.info("[Startup] Database connected")

        yield

    finally:
        # ---------------- SHUTDOWN ----------------
        if engine:
            logger.info("[Shutdown] Closing DB engine")
            await engine.dispose()

        if not settings.is_project:
            logger.info("[Shutdown] Stopping SSH tunnel")
            stop_ssh_tunnel()


app = FastAPI(
    title="Trava Zelenee",
    summary="Trava Zelenee",
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
    openapi_url="/openapi.json",
)


# --------------- Эндпоинт документации --------------
@app.get("/", tags=["API Docs"], dependencies=[Depends(verify_docs_auth)])
def swagger_ui():
    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title="Swagger UI",
    )


# --------------- Подключаем CORS --------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors.allow_origins,
    allow_credentials=settings.cors.allow_credentials,
    allow_methods=settings.cors.allow_methods,
    allow_headers=settings.cors.allow_headers,
)


# --------------- Добавляем маршрутизацию --------------
app.include_router(info_router, dependencies=[Depends(verify_api_key)])
app.include_router(location_router, dependencies=[Depends(verify_api_key)])
app.include_router(metric_router, dependencies=[Depends(verify_api_key)])


# --------------- Логгируем необходимую информацию --------------
logger.info(f"[Trava]: Приложение запущено в режиме {'PROJECT' if settings.is_project else 'DEVELOP'}")


# --------------- Запуск приложения --------------
if __name__ == "__main__":
    uvicorn.run(app, host=settings.project.host, port=settings.project.port)
