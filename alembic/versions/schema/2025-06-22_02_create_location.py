"""Создание таблиц с локациями Страна и Город

Revision ID: fc9d038a9df1
Revises: 9f7bc9e202b3
Create Date: 2025-06-22 13:10:24.995473

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "fc9d038a9df1"
down_revision: Union[str, Sequence[str], None] = "9f7bc9e202b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def create_contry():

    # --------------- Создаю таблицу со странами "country" ---------------
    op.create_table(
        "country",
        # Идентификатор страны
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False, comment="ID страны"),
        sa.Column("name", sa.String(length=255), nullable=False, comment="Название страны"),
        sa.Column("name_eng", sa.String(length=255), nullable=False, comment="Название страны ENG"),
        sa.Column("iso_code", sa.String(length=10), nullable=False, comment="Код страны ISO"),
        # Местоположение
        sa.Column("latitude", sa.Float(), nullable=False, comment="Широта"),
        sa.Column("longitude", sa.Float(), nullable=False, comment="Долгота"),
        # Характеристика страны
        sa.Column("language", sa.String(length=50), nullable=True, comment="Основной язык страны"),
        sa.Column("currency", sa.String(length=10), nullable=True, comment="Валюта страны"),
        sa.Column("timezone", sa.String(length=50), nullable=True, comment="Часовой пояс страны"),
        sa.Column("migration_policy", sa.Text(), nullable=True, comment="Краткое описание миграционной политики"),
        sa.Column("description", sa.Text(), nullable=True, comment="Описание страны"),
        sa.Column("population", sa.Integer(), nullable=True, comment="Население страныи"),
        sa.Column("climate", sa.String(length=100), nullable=True, comment="Климат страны"),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.text("true"), comment="Отображение страны"
        ),
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
        comment="Таблица стран и данными о них",
    )
    # Создаю индексы
    op.create_index("ix_country_id", "country", ["id"])
    op.create_index("ix_country_name", "country", ["name"])
    op.create_index("ix_country_name_eng", "country", ["name_eng"])
    op.create_index("ix_country_iso_code", "country", ["iso_code"])
    op.create_index("ix_country_latitude", "country", ["latitude"])
    op.create_index("ix_country_longitude", "country", ["longitude"])
    # Создаю уникальные ограничения
    op.create_unique_constraint("uq_country_name", "country", ["name"])
    op.create_unique_constraint("uq_country_name_eng", "country", ["name_eng"])
    op.create_unique_constraint("uq_country_iso_code", "country", ["iso_code"])
    op.create_unique_constraint("uq_country_coordinates", "country", ["latitude", "longitude"])
    # Создаю проверки
    op.create_check_constraint("ck_country_longitude_range", "country", "longitude BETWEEN -180 AND 180")
    op.create_check_constraint("ck_country_latitude_range", "country", "latitude BETWEEN -90 AND 90")


def delete_country():

    # Удаляю индексы, проверки для таблицы городов country
    op.drop_index("ix_country_id", table_name="country")
    op.drop_index("ix_country_iso_code", table_name="country")
    op.drop_index("ix_country_name", table_name="country")
    op.drop_index("ix_country_name_eng", table_name="country")
    op.drop_index("ix_country_latitude", table_name="country")
    op.drop_index("ix_country_longitude", table_name="country")

    op.drop_constraint("uq_country_name", "country", type_="unique")
    op.drop_constraint("uq_country_name_eng", "country", type_="unique")
    op.drop_constraint("uq_country_iso_code", "country", type_="unique")
    op.drop_constraint("uq_country_coordinates", "country", type_="unique")

    op.drop_constraint("ck_country_longitude_range", "country", type_="check")
    op.drop_constraint("ck_country_latitude_range", "country", type_="check")

    # Удаляю country
    op.drop_table("country")


def create_region():

    # --------------- Создаю таблицу со регионами "region" ---------------
    op.create_table(
        "region",
        # Идентификатор региона/страны
        sa.Column("id", sa.Integer(), primary_key=True, comment="ID региона"),
        sa.Column(
            "country_id",
            sa.Integer(),
            sa.ForeignKey("country.id", ondelete="CASCADE"),
            nullable=False,
            comment="ID страны",
        ),
        sa.Column("name", sa.String(255), nullable=False, comment="Название региона"),
        sa.Column("name_eng", sa.String(255), nullable=False, comment="Название региона ENG"),
        # Характеристика региона
        sa.Column("description", sa.Text(), nullable=True, comment="Описание региона"),
        sa.Column("language", sa.String(50), nullable=True, comment="Основной язык региона"),
        sa.Column("timezone", sa.String(50), nullable=True, comment="Часовой пояс региона"),
        sa.Column("population", sa.Integer(), nullable=True, comment="Население региона"),
        sa.Column("climate", sa.String(100), nullable=True, comment="Климат региона"),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.text("true"), comment="Отображение региона"
        ),
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
        comment="Таблица регионов и данными о них",
    )
    # Создаю индексы
    op.create_index("ix_region_id", "region", ["id"])
    op.create_index("ix_region_country_id", "region", ["country_id"])
    op.create_index("ix_region_name", "region", ["name"])
    op.create_index("ix_region_name_eng", "region", ["name_eng"])
    # Создаю ограничения
    op.create_unique_constraint("uq_region_name", "region", ["name"])
    op.create_unique_constraint("uq_region_name_eng", "region", ["name_eng"])
    op.create_unique_constraint("uq_region_country_name", "region", ["country_id", "name"])
    op.create_unique_constraint("uq_region_country_name_eng", "region", ["country_id", "name_eng"])


def delete_region():

    # Удаляю индексы, проверки для таблицы городов region
    op.drop_index("ix_region_id", table_name="region")
    op.drop_index("ix_region_country_id", table_name="region")
    op.drop_index("ix_region_name", table_name="region")
    op.drop_index("ix_region_name_eng", table_name="region")

    op.drop_constraint("uq_region_name", "region", type_="unique")
    op.drop_constraint("uq_region_name_eng", "region", type_="unique")
    op.drop_constraint("uq_region_country_name", "region", type_="unique")
    op.drop_constraint("uq_region_country_name_eng", "region", type_="unique")

    # Удаляю таблицу region
    op.drop_table("region")


def create_city():

    # --------------- Создаю таблицу с городами "city" ---------------
    op.create_table(
        "city",
        # Идентификатор города
        sa.Column("id", sa.Integer(), primary_key=True, comment="ID города"),
        sa.Column(
            "country_id",
            sa.Integer(),
            sa.ForeignKey("country.id", ondelete="CASCADE"),
            nullable=False,
            comment="ID страны",
        ),
        sa.Column(
            "region_id",
            sa.Integer(),
            sa.ForeignKey("region.id", ondelete="CASCADE"),
            nullable=True,
            comment="ID региона",
        ),
        sa.Column("name", sa.String(255), nullable=False, comment="Название города"),
        sa.Column("name_eng", sa.String(255), nullable=False, comment="Название города ENG"),
        # Местоположение
        sa.Column("latitude", sa.Float(), nullable=False, comment="Широта"),
        sa.Column("longitude", sa.Float(), nullable=False, comment="Долгота"),
        # Характеристика города
        sa.Column("is_capital", sa.Boolean(), nullable=False, server_default=sa.text("false"), comment="Столица"),
        sa.Column("timezone", sa.String(100), nullable=True, comment="Часовой пояс"),
        sa.Column("population", sa.Integer(), nullable=True, comment="Население города"),
        sa.Column("language", sa.String(50), nullable=True, comment="Основной язык"),
        sa.Column("climate", sa.String(100), nullable=True, comment="Климат"),
        sa.Column("description", sa.Text(), nullable=True, comment="Описание города"),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.text("true"), comment="Отображение города"
        ),
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
        comment="Таблица городов и данными о них",
    )
    # Создаю индексы
    op.create_index("ix_city_id", "city", ["id"])
    op.create_index("ix_city_country_id", "city", ["country_id"])
    op.create_index("ix_city_region_id", "city", ["region_id"])
    op.create_index("ix_city_name", "city", ["name"])
    op.create_index("ix_city_name_eng", "city", ["name_eng"])
    op.create_index("ix_city_latitude", "city", ["latitude"])
    op.create_index("ix_city_longitude", "city", ["longitude"])
    # Создаю уникальные ограничения
    op.create_unique_constraint("uq_city_country_name", "city", ["country_id", "name"])
    op.create_unique_constraint("uq_city_country_name_eng", "city", ["country_id", "name_eng"])
    op.create_unique_constraint("uq_city_coordinates", "city", ["latitude", "longitude"])
    # Создаю проверки
    op.create_check_constraint("ck_city_latitude_range", "city", "latitude BETWEEN -90 AND 90")
    op.create_check_constraint("ck_city_longitude_range", "city", "longitude BETWEEN -180 AND 180")
    op.create_index(
        "uq_city_capital_per_country",
        "city",
        ["country_id"],
        postgresql_where=sa.text("is_capital IS TRUE"),
    )


def delete_city():
    # Удаляю индексы таблицы городов city
    op.drop_index("uq_city_capital_per_country", table_name="city")
    op.drop_index("ix_city_longitude", table_name="city")
    op.drop_index("ix_city_latitude", table_name="city")
    op.drop_index("ix_city_name_eng", table_name="city")
    op.drop_index("ix_city_name", table_name="city")
    op.drop_index("ix_city_region_id", table_name="city")
    op.drop_index("ix_city_country_id", table_name="city")
    op.drop_index("ix_city_id", table_name="city")

    op.drop_constraint("uq_city_coordinates", "city", type_="unique")
    op.drop_constraint("uq_city_country_name_eng", "city", type_="unique")
    op.drop_constraint("uq_city_country_name", "city", type_="unique")
    op.drop_constraint("ck_city_latitude_range", "city", type_="check")
    op.drop_constraint("ck_city_longitude_range", "city", type_="check")

    # Удаляю таблицу city
    op.drop_table("city")


def upgrade() -> None:

    create_contry()
    create_region()
    create_city()


def downgrade():

    delete_city()
    delete_region()
    delete_country()
