import logging

from sqlalchemy.ext.asyncio import AsyncSession


logger = logging.getLogger(__name__)


class DB_MetricService:

    def __init__(self, async_session: AsyncSession):
        """Инициализация основных параметров."""

        self._async_session = async_session
