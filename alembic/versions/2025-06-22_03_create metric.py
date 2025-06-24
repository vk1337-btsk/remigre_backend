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


type_data_enum = sa.Enum("str", "int", "float", "range", name="type_data_enum")
type_category_enum = sa.Enum("country", "city", "country and city", name="type_category_enum")
period_type_enum = sa.Enum("one_time", "yearly", "monthly", "interval", name="period_type_enum", create_type=False)


def upgrade() -> None:

    # Создаём ENUM
    bind = op.get_bind()

    type_data_enum.create(bind, checkfirst=True)
    type_category_enum.create(bind, checkfirst=True)
    period_type_enum.create(bind, checkfirst=True)

    # Создаю таблицу с метриками
    op.create_table(
        "metric_category",
        sa.Column("id", sa.Integer(), nullable=False, comment="ID метрики"),
        sa.Column("short_name", sa.String(length=255), nullable=False, comment="Краткое название метрики"),
        sa.Column("full_name", sa.String(length=255), nullable=False, comment="Полное название метрики"),
        sa.Column("description", sa.Text(), nullable=False, comment="Описание метрики"),
        sa.Column("source", sa.String(length=255), nullable=False, comment="Источник метрики"),
        sa.Column(
            "type_data",
            postgresql.ENUM("str", "int", "float", "range", name="type_data_enum", create_type=False),
            nullable=False,
            comment="Тип данных метрики",
        ),
        sa.Column(
            "type_category",
            postgresql.ENUM("country", "city", "country and city", name="type_category_enum", create_type=False),
            nullable=False,
            comment="Объект метрики",
        ),
        sa.Column("unit_format", sa.String(length=255), nullable=False, comment="Единица измерения метрики"),
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
        sa.PrimaryKeyConstraint("id"),
        comment="Информация об используемых метриках",
    )
    op.create_index(op.f("ix_metric_category_id"), "metric_category", ["id"], unique=False)
    op.create_index(op.f("ix_metric_category_short_name"), "metric_category", ["short_name"], unique=True)

    # Создаю таблицу с периодами метрик
    op.create_table(
        "metric_period",
        sa.Column("id", sa.Integer(), nullable=False, comment="ID периода метрики"),
        sa.Column("category_id", sa.Integer(), nullable=False, comment="ID категории метрики"),
        sa.Column(
            "period_type",
            postgresql.ENUM("one_time", "yearly", "monthly", "interval", name="period_type_enum", create_type=False),
            nullable=False,
            comment="Тип периода",
        ),
        sa.Column("period_year", sa.Integer(), nullable=True, comment="Год (если указано)"),
        sa.Column("period_month", sa.Integer(), nullable=True, comment="Месяц (если указано)"),
        sa.Column("date_start", sa.DateTime(), nullable=True, comment="Начало периода (для интервала)"),
        sa.Column("date_end", sa.DateTime(), nullable=True, comment="Конец периода (для интервала)"),
        sa.Column("collected_at", sa.DateTime(), nullable=True, comment="Когда были собраны данные"),
        sa.Column("source_url", sa.String(length=512), nullable=True, comment="Источник метрики"),
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
        sa.ForeignKeyConstraint(["category_id"], ["metric_category.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        comment="Временной промежуток метрики (версия)",
    )
    op.create_index(op.f("ix_metric_period_id"), "metric_period", ["id"], unique=False)
    op.create_index(op.f("ix_metric_period_category_id"), "metric_period", ["category_id"], unique=False)

    # Создаю таблицу с данными метрик
    op.create_table(
        "metric_data",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=False, comment="ID метрики"),
        sa.Column("period_id", sa.Integer(), nullable=False, comment="ID периода"),
        sa.Column("country_id", sa.Integer(), nullable=False, comment="ID страны"),
        sa.Column("city_id", sa.Integer(), nullable=True, comment="ID города"),
        sa.Column("value", sa.String(length=255), nullable=False, comment="Значение метрики"),
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
        sa.ForeignKeyConstraint(["category_id"], ["metric_category.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["city_id"], ["city.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["country_id"], ["country.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["period_id"], ["metric_period.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        comment="Таблица с данными метрик",
    )
    op.create_index(op.f("ix_metric_data_id"), "metric_data", ["id"], unique=False)
    op.create_index(op.f("ix_metric_data_category_id"), "metric_data", ["category_id"], unique=False)
    op.create_index(op.f("ix_metric_data_period_id"), "metric_data", ["period_id"], unique=False)
    op.create_index(op.f("ix_metric_data_country_id"), "metric_data", ["country_id"], unique=False)
    op.create_index(op.f("ix_metric_data_city_id"), "metric_data", ["city_id"], unique=False)


def downgrade() -> None:

    # Удаляю таблицу с данными метрик
    op.drop_index(op.f("ix_metric_data_id"), table_name="metric_data")
    op.drop_index(op.f("ix_metric_data_category_id"), table_name="metric_data")
    op.drop_index(op.f("ix_metric_data_period_id"), table_name="metric_data")
    op.drop_index(op.f("ix_metric_data_country_id"), table_name="metric_data")
    op.drop_index(op.f("ix_metric_data_city_id"), table_name="metric_data")
    op.drop_table("metric_data")

    # Удаляю таблицу с периодами метрик
    op.drop_index(op.f("ix_metric_period_id"), table_name="metric_period")
    op.drop_index(op.f("ix_metric_period_category_id"), table_name="metric_period")
    op.drop_table("metric_period")

    # Удаляю таблицу с категориями метрик
    op.drop_index(op.f("ix_metric_category_id"), table_name="metric_category")
    op.drop_index(op.f("ix_metric_category_short_name"), table_name="metric_category")
    op.drop_table("metric_category")

    # Удаляем ENUM отдельно
    period_type_enum.drop(op.get_bind())
    type_category_enum.drop(op.get_bind())
    type_data_enum.drop(op.get_bind())
