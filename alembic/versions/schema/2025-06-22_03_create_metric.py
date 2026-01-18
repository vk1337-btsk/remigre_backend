"""Создание таблиц с метриками

Revision ID: b898e1587fb7
Revises: fc9d038a9df1
Create Date: 2025-06-22 15:30:10.154054

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "b898e1587fb7"
down_revision: Union[str, Sequence[str], None] = "fc9d038a9df1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ENUM-типы
type_data_enum = postgresql.ENUM("INT", "STRING", "FLOAT", "RANGE", "BOOL", name="type_data_enum", create_type=False)
period_type_enum = postgresql.ENUM(
    "ONE_TIME", "YEARLY", "MONTHLY", "WEEKLY", "INTERVAL", "NONE", name="period_type_enum", create_type=False
)
category_metric_enum = postgresql.ENUM(
    "ECONOMY",
    "SECURITY",
    "QUALITY_OF_LIFE",
    "EMIGRATION",
    "UNCATEGORIZED",
    name="category_metric_enum",
    create_type=False,
)


# -------------------- Метрики --------------------
def create_metric_info_table():
    """Создание таблицы metric_info"""

    # Создаём последовательность
    op.execute("CREATE SEQUENCE IF NOT EXISTS metric_info_id_seq START WITH 1 INCREMENT BY 1;")

    # Создаю таблицу
    op.create_table(
        "metric_info",
        # ID
        sa.Column(
            "id",
            sa.Integer(),
            server_default=sa.text("nextval('metric_info_id_seq')"),
            primary_key=True,
            nullable=False,
            comment="ID",
        ),
        # Основные данные
        sa.Column("slug", sa.String(length=255), nullable=False, comment="Slug"),
        sa.Column("name", sa.String(length=255), nullable=False, comment="Название"),
        sa.Column("description", sa.Text(), nullable=True, comment="Описание"),
        sa.Column("category", category_metric_enum, nullable=False, comment="Категория"),
        # Характеристики метрики и его источник
        sa.Column("source_name", sa.String(length=255), nullable=True, comment="Источник"),
        sa.Column("source_url", sa.String(length=512), nullable=True, comment="URL источника"),
        sa.Column("type_data", type_data_enum, nullable=False, comment="Тип данных"),
        # Дополнительно
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true"), comment="Флаг активности"),
        sa.Column("add_info", postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment="Доп. информация"),
        # Время и дата создания/обновления
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
            comment="Дата создания",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            server_onupdate=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
            comment="Дата обновления",
        ),
        comment="Индикатор метрики",
    )

    # Создаю индексы
    op.create_index("ix_metric_info_slug", "metric_info", ["slug"])

    # Создаю уникальные ограничения
    op.create_unique_constraint("uq_metric_info_slug", "metric_info", ["slug"])


def drop_metric_info_table():
    """Удаление таблицы metric_info"""

    # Удаляю индексы
    op.drop_index("ix_metric_info_slug", table_name="metric_info")

    # Удаляю таблицу
    op.drop_table("metric_info")

    # Удаляю последовательности
    op.execute("DROP SEQUENCE IF EXISTS metric_info_id_seq;")

# -------------------- Серии --------------------
def create_metric_series_table():
    """Создание таблицы metric_series"""

    # Создаём последовательность
    op.execute("CREATE SEQUENCE IF NOT EXISTS metric_series_id_seq START WITH 1 INCREMENT BY 1;")

    # Создаю таблицу
    op.create_table(
        "metric_series",
        # ID
        sa.Column(
            "id",
            sa.Integer(),
            server_default=sa.text("nextval('metric_series_id_seq')"),
            primary_key=True,
            comment="ID",
        ),
        # Связи
        sa.Column(
            "metric_id",
            sa.Integer(),
            sa.ForeignKey("metric_info.id", ondelete="CASCADE"),
            nullable=False,
            comment="ID метрики",
        ),
        # Дополнительные измерения / разрезы серий
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False, comment="Флаг активности"),
        sa.Column("add_info", postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment="Доп. информация"),
        # Время и дата создания/обновления
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
            comment="Дата создания",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
            comment="Дата обновления",
        ),
    )

    # Создаю индексы
    op.create_index("ix_metric_series_metric_id", "metric_series", ["metric_id"])


def drop_metric_series_table():
    """Удаление таблицы metric_series"""

    # Удаляю индексы
    op.drop_index("ix_metric_series_metric_id", table_name="metric_series")

    # Удаляю таблицу
    op.drop_table("metric_series")

    # Удаляю последовательности
    op.execute("DROP SEQUENCE IF EXISTS metric_series_id_seq;")

# -------------------- Периоды --------------------
def create_metric_period_table():
    """Создание таблицы metric_period"""

    # Создаём последовательность
    op.execute("CREATE SEQUENCE IF NOT EXISTS metric_period_id_seq START WITH 1 INCREMENT BY 1;")

    # Создаю таблицу
    op.create_table(
        "metric_period",
        # ID
        sa.Column(
            "id",
            sa.Integer(),
            server_default=sa.text("nextval('metric_period_id_seq')"),
            primary_key=True,
            nullable=False,
            comment="ID периода",
        ),
        # Связи
        sa.Column(
            "series_id",
            sa.Integer(),
            sa.ForeignKey("metric_series.id", ondelete="CASCADE"),
            nullable=False,
            comment="ID серии",
        ),
        # Период
        sa.Column("period_type", period_type_enum, nullable=False, comment="Тип периода метрики"),
        sa.Column("period_year", sa.Integer(), nullable=True, comment="Год"),
        sa.Column("period_month", sa.Integer(), nullable=True, comment="Месяц"),
        sa.Column("period_week", sa.Integer(), nullable=True, comment="Неделя"),
        # Интервал
        sa.Column("date_start", sa.DateTime(), nullable=True, comment="Начало периода"),
        sa.Column("date_end", sa.DateTime(), nullable=True, comment="Конец периода"),
        sa.Column("collected_at", sa.DateTime(), nullable=True, comment="Дата сбора"),
        # Дополнительно
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False, comment="Флаг активности"),
        sa.Column(
            "add_info", postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment="Дополнительная информация"
        ),
        # Время и дата создания/обновления
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
            comment="Дата создания",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            server_onupdate=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
            comment="Дата обновления",
        ),
        comment="Временной промежуток метрики (версия)",
    )

    # Создаю индексы
    op.create_index("ix_metric_period_id", "metric_period", ["id"])
    op.create_index("ix_metric_period_series_id", "metric_period", ["series_id"])
    op.create_index("ix_metric_period_period_type", "metric_period", ["period_type"])
    op.create_index("ix_metric_period_period_year", "metric_period", ["period_year"])
    op.create_index("ix_metric_period_period_month", "metric_period", ["period_month"])
    op.create_index("ix_metric_period_period_week", "metric_period", ["period_week"])

    # Создаю ограничения
    op.create_check_constraint(
        constraint_name="ck_period_year_nonnegative",
        table_name="metric_period",
        condition="(period_year IS NULL) OR (period_year >= 0)",
    )
    op.create_check_constraint(
        constraint_name="ck_period_month_range",
        table_name="metric_period",
        condition="(period_month IS NULL) OR (period_month BETWEEN 1 AND 12)",
    )
    op.create_check_constraint(
        constraint_name="ck_period_week_range",
        table_name="metric_period",
        condition="(period_week IS NULL) OR (period_week BETWEEN 1 AND 55)",
    )


def drop_metric_period_table():
    """Удаление таблицы metric_period"""

    # Удаляю ограничения
    op.drop_constraint("ck_period_week_range", "metric_period", type_="check")
    op.drop_constraint("ck_period_month_range", "metric_period", type_="check")
    op.drop_constraint("ck_period_year_nonnegative", "metric_period", type_="check")

    # Удаляю индексы
    op.drop_index("ix_metric_period_period_week", table_name="metric_period")
    op.drop_index("ix_metric_period_period_month", table_name="metric_period")
    op.drop_index("ix_metric_period_period_year", table_name="metric_period")
    op.drop_index("ix_metric_period_period_type", table_name="metric_period")
    op.drop_index("ix_metric_period_id", table_name="metric_period")
    op.drop_index("ix_metric_period_series_id", table_name="metric_period")

    # Удаляю таблицу
    op.drop_table("metric_period")

    # Удаляю последовательности
    op.execute("DROP SEQUENCE IF EXISTS metric_period_id_seq;")

# -------------------- Данные --------------------
def create_metric_data_table():
    """Создание таблицы metric_data"""

    # Создаём последовательность
    op.execute("CREATE SEQUENCE IF NOT EXISTS metric_data_id_seq START WITH 1 INCREMENT BY 1;")

    # Создаю таблицу
    op.create_table(
        "metric_data",
        # ID
        sa.Column(
            "id",
            sa.Integer(),
            server_default=sa.text("nextval('metric_data_id_seq')"),
            nullable=False,
            primary_key=True,
            comment="ID",
        ),
        # Связи
        sa.Column(
            "series_id",
            sa.Integer(),
            sa.ForeignKey("metric_series.id", ondelete="CASCADE"),
            nullable=False,
            comment="ID серии",
        ),
        sa.Column(
            "period_id",
            sa.Integer(),
            sa.ForeignKey("metric_period.id", ondelete="CASCADE"),
            nullable=False,
            comment="ID периода",
        ),
        sa.Column(
            "country_id",
            sa.Integer(),
            sa.ForeignKey("loc_country.id", ondelete="CASCADE"),
            nullable=True,
            comment="ID страны",
        ),
        sa.Column(
            "city_id",
            sa.Integer(),
            sa.ForeignKey("loc_city.id", ondelete="CASCADE"),
            nullable=True,
            comment="ID города",
        ),
        # Значение метрики
        sa.Column("value_int", sa.Integer(), nullable=True),
        sa.Column("value_string", sa.String(length=255), nullable=True),
        sa.Column("value_float", sa.Float(), nullable=True),
        sa.Column("value_range_min", sa.Float(), nullable=True),
        sa.Column("value_range_max", sa.Float(), nullable=True),
        sa.Column("value_bool", sa.Boolean(), nullable=True),
        # Дополнительно
        sa.Column("add_info", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        # Время и дата создания/обновления
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            server_onupdate=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        comment="Таблица с данными метрик",
    )

    # Создаю индексы
    op.create_index(op.f("ix_metric_data_id"), "metric_data", ["id"])
    op.create_index(op.f("ix_metric_data_period_id"), "metric_data", ["period_id"])
    op.create_index("ix_metric_data_series_id", "metric_data", ["series_id"])
    op.create_index(op.f("ix_metric_data_country_id"), "metric_data", ["country_id"])
    op.create_index(op.f("ix_metric_data_city_id"), "metric_data", ["city_id"])
    op.create_index(op.f("ix_metric_data_value_int"), "metric_data", ["value_int"])
    op.create_index(op.f("ix_metric_data_value_float"), "metric_data", ["value_float"])
    op.create_index(op.f("ix_metric_data_value_range_min"), "metric_data", ["value_range_min"])
    op.create_index(op.f("ix_metric_data_value_range_max"), "metric_data", ["value_range_max"])

    # Создаю уникальные ограничения
    op.create_unique_constraint(
        constraint_name="uq_metric_data_entries",
        table_name="metric_data",
        columns=["series_id", "period_id", "country_id", "city_id"],
    )

    # Создаю ограничения
    op.create_check_constraint(
        constraint_name="ck_metric_data_city_or_country_not_null",
        table_name="metric_data",
        condition="(city_id IS NOT NULL) OR (country_id IS NOT NULL)",
    )
    op.create_check_constraint(
        constraint_name="ck_metric_data_range_min_lte_max",
        table_name="metric_data",
        condition="(value_range_min IS NULL OR value_range_max IS NULL) OR (value_range_min <= value_range_max)",
    )
    op.create_check_constraint(
        constraint_name="ck_metric_data_only_one_value_filled",
        table_name="metric_data",
        condition="""
        (
            (CASE WHEN value_int IS NOT NULL THEN 1 ELSE 0 END) +
            (CASE WHEN value_float IS NOT NULL THEN 1 ELSE 0 END) +
            (CASE WHEN value_range_min IS NOT NULL OR value_range_max IS NOT NULL THEN 1 ELSE 0 END) +
            (CASE WHEN value_bool IS NOT NULL THEN 1 ELSE 0 END) +
            (CASE WHEN value_string IS NOT NULL THEN 1 ELSE 0 END)
        ) = 1
        """,
    )


def drop_metric_data_table():
    """Удаление таблицы metric_data"""

    # Удаляю ограничения
    op.drop_constraint("ck_metric_data_only_one_value_filled", "metric_data", type_="check")
    op.drop_constraint("ck_metric_data_range_min_lte_max", "metric_data", type_="check")
    op.drop_constraint("ck_metric_data_city_or_country_not_null", "metric_data", type_="check")

    # Удаляю уникальные ограничения
    op.drop_constraint("uq_metric_data_entries", "metric_data", type_="unique")

    # Удаляю индексы
    op.drop_index("ix_metric_data_value_range_max", table_name="metric_data")
    op.drop_index("ix_metric_data_value_range_min", table_name="metric_data")
    op.drop_index("ix_metric_data_value_float", table_name="metric_data")
    op.drop_index("ix_metric_data_value_int", table_name="metric_data")
    op.drop_index("ix_metric_data_city_id", table_name="metric_data")
    op.drop_index("ix_metric_data_country_id", table_name="metric_data")
    op.drop_index("ix_metric_data_period_id", table_name="metric_data")
    op.drop_index("ix_metric_data_id", table_name="metric_data")
    op.drop_index("ix_metric_data_series_id", table_name="metric_data")

    # Удаляю таблицу
    op.drop_table("metric_data")

    # Удаляю последовательности
    op.execute("DROP SEQUENCE IF EXISTS metric_data_id_seq;")


#
#
# ==================== Миграция создания и удаления таблиц ====================
def upgrade() -> None:

    # Создаём ENUM отдельно
    type_data_enum.create(op.get_bind(), checkfirst=True)
    category_metric_enum.create(op.get_bind(), checkfirst=True)
    period_type_enum.create(op.get_bind(), checkfirst=True)

    create_metric_info_table()
    create_metric_series_table()
    create_metric_period_table()
    create_metric_data_table()


def downgrade() -> None:

    drop_metric_data_table()
    drop_metric_period_table()
    drop_metric_series_table()
    drop_metric_info_table()

    # Удаляем ENUM отдельно
    period_type_enum.drop(op.get_bind(), checkfirst=True)
    category_metric_enum.drop(op.get_bind(), checkfirst=True)
    type_data_enum.drop(op.get_bind(), checkfirst=True)
