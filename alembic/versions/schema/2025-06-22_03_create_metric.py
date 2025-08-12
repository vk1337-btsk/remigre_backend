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


type_data_enum = postgresql.ENUM("int", "string", "float", "range", "bool", name="type_data_enum", create_type=False)
period_type_enum = postgresql.ENUM(
    "one_time",
    "yearly",
    "monthly",
    "weekly",
    "interval",
    "none",
    name="period_type_enum",
    create_type=False,
)
category_metric_enum = postgresql.ENUM(
    "economy",
    "security",
    "quality of life",
    "emigration",
    "uncategorized",
    name="category_metric_enum",
    create_type=False,
)


def upgrade() -> None:

    # Создаём ENUM отдельно
    type_data_enum.create(op.get_bind(), checkfirst=True)
    category_metric_enum.create(op.get_bind(), checkfirst=True)
    period_type_enum.create(op.get_bind(), checkfirst=True)

    # ---------------Создаю таблицу с метриками "metric_info" ---------------
    op.create_table(
        "metric_info",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False, comment="ID метрики"),
        sa.Column(
            "slug", sa.String(length=255), nullable=False, comment="Slug метрики (нужен как текстовой идентификатор)"
        ),
        sa.Column("name", sa.String(length=255), nullable=False, comment="Название метрики"),
        sa.Column("description", sa.Text(), nullable=True, comment="Описание метрики"),
        sa.Column("category", category_metric_enum, nullable=False, comment="Категория метрики"),
        # Характеристики метрики
        sa.Column("source_name", sa.String(length=255), nullable=True, comment="Название источника метрики"),
        sa.Column("source_url", sa.String(length=255), nullable=True, comment="URL источника метрики"),
        sa.Column("type_data", type_data_enum, nullable=False, comment="Тип данных метрики (int/str/range/bool)"),
        sa.Column("unit_format", sa.String(length=255), nullable=False, comment="Единица измерения метрики"),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.text("true"), comment="Активность метрики"
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
            comment="Дата создания",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            server_onupdate=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
            comment="Дата обновления",
        ),
        comment="Информация об используемых метриках",
    )
    # Создаю индексы
    op.create_index("ix_metric_info_slug", "metric_info", ["slug"])
    # Создаю уникальные ограничения
    op.create_unique_constraint("uq_metric_info_id", "metric_info", ["id"])

    # ---------------Создаю таблицу с периодами метрик "metric_period" ---------------
    op.create_table(
        "metric_period",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False, comment="ID периода"),
        # Связь с метрикой
        sa.Column(
            "metric_id",
            sa.Integer(),
            sa.ForeignKey("metric_info.id", ondelete="CASCADE"),
            nullable=False,
            comment="ID метрики",
        ),
        # Период
        sa.Column("period_type", period_type_enum, nullable=False, comment="Тип периода метрики"),
        sa.Column("period_year", sa.Integer(), nullable=True, comment="Год (если указано)"),
        sa.Column("period_month", sa.Integer(), nullable=True, comment="Месяц (если указано)"),
        sa.Column("period_week", sa.Integer(), nullable=True, comment="Неделя (если указано)"),
        # Интервал
        sa.Column("date_start", sa.DateTime(), nullable=True, comment="Начало периода (для интервала)"),
        sa.Column("date_end", sa.DateTime(), nullable=True, comment="Конец периода (для интервала)"),
        # Информация о получении данных
        sa.Column("collected_at", sa.DateTime(), nullable=True, comment="Когда были собраны данные"),
        sa.Column("source_url", sa.String(length=512), nullable=True, comment="Источник метрики"),
        # Время создания/изменения
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
            comment="Дата создания",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            server_onupdate=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
            comment="Дата обновления",
        ),
        comment="Временной промежуток метрики (версия)",
    )
    # Создаю индексы
    op.create_index("ix_metric_period_id", "metric_period", ["id"])
    op.create_index("ix_metric_period_metric_id", "metric_period", ["metric_id"])
    op.create_index("ix_metric_period_period_type", "metric_period", ["period_type"])
    op.create_index("ix_metric_period_period_year", "metric_period", ["period_year"])
    op.create_index("ix_metric_period_period_month", "metric_period", ["period_month"])
    op.create_index("ix_metric_period_period_week", "metric_period", ["period_week"])
    # Создаю проверки
    op.create_check_constraint(
        "ck_period_year_nonnegative", "metric_period", "(period_year IS NULL) OR (period_year >= 0)"
    )
    op.create_check_constraint(
        "ck_period_month_range", "metric_period", "(period_month IS NULL) OR (period_month BETWEEN 1 AND 12)"
    )
    op.create_check_constraint(
        "ck_period_week_range", "metric_period", "(period_week IS NULL) OR (period_week BETWEEN 1 AND 55)"
    )

    # ---------------Создаю таблицу с данными метрик "metric_data" ---------------
    op.create_table(
        "metric_data",
        sa.Column("id", sa.Integer(), nullable=False),
        # Связь с метриками
        sa.Column(
            "metric_id",
            sa.Integer(),
            sa.ForeignKey("metric_info.id", ondelete="CASCADE"),
            nullable=False,
            comment="ID метрики",
        ),
        sa.Column(
            "period_id",
            sa.Integer(),
            sa.ForeignKey("metric_period.id", ondelete="CASCADE"),
            nullable=False,
            comment="ID периода",
        ),
        # Связь с локациями
        sa.Column(
            "country_id",
            sa.Integer(),
            sa.ForeignKey("country.id", ondelete="CASCADE"),
            nullable=False,
            comment="ID страны",
        ),
        sa.Column(
            "city_id",
            sa.Integer(),
            sa.ForeignKey("city.id", ondelete="CASCADE"),
            nullable=True,
            comment="ID города",
        ),
        # Значение метрики
        sa.Column("value_int", sa.Integer(), nullable=True, comment="Значение в формате INT/NUMERIC"),
        sa.Column("value_string", sa.String(length=255), nullable=True, comment="Значение в формате STRING"),
        sa.Column("value_float", sa.Float(), nullable=True, comment="Значение в формате FLOAT"),
        sa.Column("value_range_min", sa.Integer(), nullable=True, comment="Значение в формате MIN RANGE"),
        sa.Column("value_range_max", sa.Integer(), nullable=True, comment="Значение в формате MAX RANGE"),
        sa.Column("value_bool", sa.Boolean(), nullable=True, comment="Значение BOOL"),
        # Время создания/изменения
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
            comment="Дата создания",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            server_onupdate=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
            comment="Дата обновления",
        ),
        comment="Таблица с данными метрик",
    )
    # Создаю индексы
    op.create_index(op.f("ix_metric_data_id"), "metric_data", ["id"])
    op.create_index(op.f("ix_metric_data_metric_id"), "metric_data", ["metric_id"])
    op.create_index(op.f("ix_metric_data_period_id"), "metric_data", ["period_id"])
    op.create_index(op.f("ix_metric_data_country_id"), "metric_data", ["country_id"])
    op.create_index(op.f("ix_metric_data_city_id"), "metric_data", ["city_id"])
    op.create_index(op.f("ix_metric_data_value_int"), "metric_data", ["value_int"])
    op.create_index(op.f("ix_metric_data_value_float"), "metric_data", ["value_float"])
    op.create_index(op.f("ix_metric_data_value_range_min"), "metric_data", ["value_range_min"])
    op.create_index(op.f("ix_metric_data_value_range_max"), "metric_data", ["value_range_max"])
    # Создаю уникальные ограничения
    op.create_unique_constraint(
        "uq_metric_data_unique_metric_period_location",
        "metric_data",
        ["metric_id", "period_id", "country_id", "city_id"],
    )
    # Создаю проверки
    op.create_check_constraint(
        "ck_metric_data_city_or_country_not_null", "metric_data", "(city_id IS NOT NULL) OR (country_id IS NOT NULL)"
    )
    op.create_check_constraint(
        "ck_metric_data_range_min_lte_max",
        "metric_data",
        "(value_range_min IS NULL OR value_range_max IS NULL) OR (value_range_min <= value_range_max)",
    )
    op.create_check_constraint(
        "ck_metric_data_only_one_value_filled",
        "metric_data",
        """
            (
                (CASE WHEN value_int IS NOT NULL THEN 1 ELSE 0 END) +
                (CASE WHEN value_float IS NOT NULL THEN 1 ELSE 0 END) +
                (CASE WHEN value_range_min IS NOT NULL OR value_range_max IS NOT NULL THEN 1 ELSE 0 END) +
                (CASE WHEN value_bool IS NOT NULL THEN 1 ELSE 0 END) +
                (CASE WHEN value_string IS NOT NULL THEN 1 ELSE 0 END)
            ) = 1
            """,
    )


def downgrade() -> None:

    # Удаляю индексы таблицы metric_data
    op.drop_constraint("ck_metric_data_only_one_value_filled", "metric_data", type_="check")
    op.drop_constraint("ck_metric_data_range_min_lte_max", "metric_data", type_="check")
    op.drop_constraint("ck_metric_data_city_or_country_not_null", "metric_data", type_="check")
    op.drop_constraint("uq_metric_data_unique_metric_period_location", "metric_data", type_="unique")
    op.drop_index("ix_metric_data_value_range_max", table_name="metric_data")
    op.drop_index("ix_metric_data_value_range_min", table_name="metric_data")
    op.drop_index("ix_metric_data_value_float", table_name="metric_data")
    op.drop_index("ix_metric_data_value_int", table_name="metric_data")
    op.drop_index("ix_metric_data_city_id", table_name="metric_data")
    op.drop_index("ix_metric_data_country_id", table_name="metric_data")
    op.drop_index("ix_metric_data_period_id", table_name="metric_data")
    op.drop_index("ix_metric_data_metric_id", table_name="metric_data")
    op.drop_index("ix_metric_data_id", table_name="metric_data")

    # Удаляю таблицу metric_data
    op.drop_table("metric_data")

    # Удаляю индексы таблицы metric_period
    op.drop_constraint("ck_period_week_range", "metric_period", type_="check")
    op.drop_constraint("ck_period_month_range", "metric_period", type_="check")
    op.drop_constraint("ck_period_year_nonnegative", "metric_period", type_="check")
    op.drop_index("ix_metric_period_period_week", table_name="metric_period")
    op.drop_index("ix_metric_period_period_month", table_name="metric_period")
    op.drop_index("ix_metric_period_period_year", table_name="metric_period")
    op.drop_index("ix_metric_period_period_type", table_name="metric_period")
    op.drop_index("ix_metric_period_metric_id", table_name="metric_period")
    op.drop_index("ix_metric_period_id", table_name="metric_period")

    # Удаляю таблицу metric_period
    op.drop_table("metric_period")

    # Удаляю индексы таблицы metric_info
    op.drop_index("ix_metric_info_slug", table_name="metric_info")
    op.drop_constraint("uq_metric_info_id", "metric_info", type_="unique")

    # Удаляем таблицу metric_info
    op.drop_table("metric_info")

    # Удаляем ENUM-типы
    period_type_enum.drop(op.get_bind(), checkfirst=True)
    category_metric_enum.drop(op.get_bind(), checkfirst=True)
    type_data_enum.drop(op.get_bind(), checkfirst=True)
