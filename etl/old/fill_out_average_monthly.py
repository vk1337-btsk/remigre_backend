"""
Зачин для импорта CSV (ILO earnings) в нашу БД через SQLAlchemy (async).

⚠️ ВАЖНО: это заготовка. В отмеченных местах TODO/DECIDE нужно:
- уточнить какие ещё столбцы из CSV сохраняем и где именно (в model fields vs JSON add_info);
- утвердить финальные значения enums (PeriodTypeEnum, CategoryMetricEnum, TypeDataEnum);
- уточнить правила создания/поиска метрик (slug, unit_format, source_url и т.п.);
- решить, в какую метрику пишем разные currency/PPP варианты (отдельные метрики или одна метрика + unit_format в периоде/значении).
"""

import asyncio
import csv
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# === Импорт моделей/enum'ов вашего проекта ===
from src.core.database.db_config import AsyncSessionLocal  # fileciteturn0file0
from src.ms_location.country import CountryModel  # fileciteturn0file4
from src.ms_metric.data import MetricDataModel  # fileciteturn0file1
from src.ms_metric.enums import (  # noqa: F401
    CategoryMetricEnum,
    PeriodTypeEnum,
    TypeDataEnum,
)
from src.ms_metric.metric import MetricModel  # fileciteturn0file2
from src.ms_metric.period import MetricPeriodModel  # fileciteturn0file3


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# === 1) Нормализация стран ===
_COUNTRY_MAP_RAW = {
    "bolivia (plurinational state of)": "Bolivia",
    "brunei darussalam": "Brunei",
    "côte d'ivoire": "Ivory Coast",
    "hong kong, china": "Hong Kong",
    "lao people's democratic republic": "Laos",
    "macao, china": "Macao",
    "occupied palestinian territory": "Palestine",
    "republic of korea": "South Korea",
    "republic of moldova": "Moldova",
    "russian federation": "Russia",
    "tanzania, united republic of": "Tanzania",
    # Особый случай: одна строка CSV -> две страны в БД
    "united kingdom of great britain and northern ireland": ["Great Britain", "Ireland"],
    "united states of america": "USA",
    "venezuela (bolivarian republic of)": "Venezuela",
    "viet nam": "Vietnam",
}


def normalize_country_names(csv_country: str) -> list[str]:
    key = (csv_country or "").strip().lower()
    mapped = _COUNTRY_MAP_RAW.get(key)
    if mapped is None:
        # по умолчанию возвращаем исходное имя как есть — БД попытаемся найти по name_eng/name
        return [csv_country.strip()]
    if isinstance(mapped, str):
        return [mapped]
    return list(mapped)


# === 2) Схема CSV ===
@dataclass
class CsvRow:
    ref_area_label: str
    source_label: str
    indicator_label: str
    sex_label: str
    classif1_label: str
    classif2_label: str
    time_year: str
    obs_value: Optional[float]
    obs_status_label: Optional[str]
    note_classif_label: Optional[str]
    note_indicator_label: Optional[str]
    note_source_label: Optional[str]

    @classmethod
    def from_dict(cls, d: dict[str, str]) -> "CsvRow":
        def _num(x: Optional[str]) -> Optional[float]:
            try:
                return (
                    float(x)
                    if x
                    not in (
                        None,
                        "",
                    )
                    else None
                )
            except Exception:
                return None

        return cls(
            ref_area_label=d.get("ref_area.label", ""),
            source_label=d.get("source.label", ""),
            indicator_label=d.get("indicator.label", ""),
            sex_label=d.get("sex.label", ""),
            classif1_label=d.get("classif1.label", ""),
            classif2_label=d.get("classif2.label", ""),
            time_year=d.get("time", ""),
            obs_value=_num(d.get("obs_value")),
            obs_status_label=d.get("obs_status.label"),
            note_classif_label=d.get("note_classif.label"),
            note_indicator_label=d.get("note_indicator.label"),
            note_source_label=d.get("note_source.label"),
        )


# === 3) Вспомогательные функции ===


def slugify(text: str) -> str:
    import re

    s = text.lower().strip()
    s = re.sub(r"[\s/]+", "-", s)
    s = re.sub(r"[^a-z0-9\-]+", "", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s or "metric"


async def get_or_create_country_ids(session: AsyncSession, csv_country: str) -> list[int]:
    target_names = normalize_country_names(csv_country)
    ids: list[int] = []
    for name in target_names:
        # Ищем по английскому имени, затем по локальному
        stmt = select(CountryModel).where((CountryModel.name_eng == name) | (CountryModel.name == name))
        res = (await session.execute(stmt)).scalar_one_or_none()
        if not res:
            logger.warning("Страна '%s' не найдена в БД (поиск по name/name_eng)", name)
            continue
        ids.append(res.id)
    return ids


async def get_or_create_metric(
    session: AsyncSession,
    *,
    indicator_label: str,
    source_label: str,
    classif1_label: str,
    classif2_label: str,
) -> MetricModel:
    """Базовая стратегия: 1 CSV-индикатор -> 1 метрика (slug по indicator_label).
    TODO/DECIDE: возможно, currency vs 2021 PPP $ должны стать отдельными метриками ИЛИ храниться в unit_format.
    TODO/DECIDE: задать category, type_data, unit_format, source_url по согласованию.
    """
    slug = slugify(indicator_label)

    # TODO/DECIDE: финальные значения
    category = CategoryMetricEnum.economy  # <- пример, заменить на нужное
    type_data = TypeDataEnum.float  # значения в CSV — вещественные
    unit_format = "TODO_unit"  # например: "currency" или конкретная строка из classif2_label

    # пробуем найти
    stmt = select(MetricModel).where(MetricModel.slug == slug)
    metric = (await session.execute(stmt)).scalar_one_or_none()
    if metric:
        return metric

    metric = MetricModel(
        slug=slug,
        name=indicator_label,
        description=f"Source: {source_label}",  # TODO/DECIDE: обогатить
        category=category,
        source_name=source_label,
        source_url=None,  # TODO/DECIDE
        type_data=type_data,
        unit_format=unit_format,
        is_active=True,
    )
    session.add(metric)
    await session.flush()  # получим metric.id без коммита
    return metric


async def get_or_create_period(session: AsyncSession, metric_id: int, year_str: str) -> MetricPeriodModel:
    # TODO/DECIDE: выбрать корректное значение enum
    period_type = PeriodTypeEnum.YEARLY

    try:
        year = int(year_str)
    except Exception:
        year = None

    stmt = select(MetricPeriodModel).where(
        (MetricPeriodModel.metric_id == metric_id)
        & (MetricPeriodModel.period_type == period_type)
        & (MetricPeriodModel.period_year == year)
    )
    period = (await session.execute(stmt)).scalar_one_or_none()
    if period:
        return period

    period = MetricPeriodModel(
        metric_id=metric_id,
        period_type=period_type,
        period_year=year,
        # TODO/DECIDE: collected_at/source_url при необходимости
    )
    session.add(period)
    await session.flush()
    return period


async def insert_value(
    session: AsyncSession,
    *,
    metric: MetricModel,
    period: MetricPeriodModel,
    country_id: int,
    row: CsvRow,
) -> None:
    """Вставка значения с учётом ограничений MetricDataModel.
    В модели допустим только ОДИН тип значения — пишем value_float.
    Остальное — в add_info (JSONB).
    TODO/DECIDE: при необходимости распаковать sex/classif в отдельные таблицы/ссылки.
    """
    data = MetricDataModel(
        metric_id=metric.id,
        period_id=period.id,
        country_id=country_id,
        value_float=row.obs_value,
        add_info={
            # --- оставляем явные места для расширения ---
            "sex": row.sex_label,  # TODO/DECIDE: нормализовать/референтные словари
            "classif1": row.classif1_label,  # TODO/DECIDE
            "classif2": row.classif2_label,  # TODO/DECIDE
            "obs_status": row.obs_status_label,
            "notes": {
                "classif": row.note_classif_label,
                "indicator": row.note_indicator_label,
                "source": row.note_source_label,
            },
            # Пример: сохранить исходный unit из classif2_label, если это валюта/PPP
            "unit_hint": row.classif2_label,  # TODO/DECIDE: возможно перенос в metric.unit_format
        },
    )
    session.add(data)


# === 4) Основной пайплайн ===


async def load_csv(csv_path: Path, *, dry_run: bool = True, batch_size: int = 1000) -> None:
    """Читает CSV и пишет данные в БД.
    - dry_run=True: всё откатываем после проверки (для теста схемы и логов);
    - batch_size: периодический commit (если not dry_run).
    """
    async with AsyncSessionLocal() as session:  # fileciteturn0file0
        tx = await session.begin()
        try:
            with csv_path.open("r", newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                counter = 0
                for raw in reader:
                    row = CsvRow.from_dict(raw)

                    # 1) метрика
                    metric = await get_or_create_metric(
                        session,
                        indicator_label=row.indicator_label,
                        source_label=row.source_label,
                        classif1_label=row.classif1_label,
                        classif2_label=row.classif2_label,
                    )

                    # 2) период
                    period = await get_or_create_period(session, metric.id, row.time_year)

                    # 3) страны (возможно несколько из одной строки)
                    country_ids = await get_or_create_country_ids(session, row.ref_area_label)
                    if not country_ids:
                        logger.warning("Пропускаем строку: нет сопоставления страны для '%s'", row.ref_area_label)
                        continue

                    # 4) значения
                    for cid in country_ids:
                        await insert_value(session, metric=metric, period=period, country_id=cid, row=row)
                        counter += 1

                    # батчевый коммит
                    if not dry_run and counter and counter % batch_size == 0:
                        await session.commit()
                        logger.info("Committed batch: %s records", counter)

            if dry_run:
                await tx.rollback()
                logger.info("Dry-run завершён. Все изменения откатили.")
            else:
                await tx.commit()
                logger.info("Импорт завершён. Всего записей: %s", counter)
        except Exception:
            logger.exception("Ошибка импорта, откатываем транзакцию.")
            await tx.rollback()
            raise


# === 5) CLI-обёртка ===

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Импорт CSV в БД (заготовка)")
    parser.add_argument("csv", type=Path, help="Путь к CSV")
    parser.add_argument("--apply", action="store_true", help="Применить изменения (по умолчанию dry-run)")
    parser.add_argument("--batch", type=int, default=1000, help="Размер батча для commit")
    args = parser.parse_args()

    asyncio.run(load_csv(args.csv, dry_run=not args.apply, batch_size=args.batch))
