"""Создание таблиц с локациями Страна и Город

Revision ID: fc9d038a9df1
Revises: 9f7bc9e202b3
Create Date: 2025-06-22 13:10:24.995473

"""

from typing import Sequence, Union

import sqlalchemy as sa
from geoalchemy2 import Geometry

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "fc9d038a9df1"
down_revision: Union[str, Sequence[str], None] = "9f7bc9e202b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def create_contry():
    """Создаю таблицу loc_country"""

    # Создаём последовательность
    op.execute("CREATE SEQUENCE IF NOT EXISTS loc_country_id_seq START WITH 1 INCREMENT BY 1;")

    # Создаю таблицу
    op.create_table(
        "loc_country",
        # Идентификатор страны
        sa.Column(
            "id",
            sa.Integer(),
            server_default=sa.text("nextval('loc_country_id_seq')"),
            primary_key=True,
            nullable=False,
            comment="ID страны",
        ),
        sa.Column("name", sa.String(length=255), nullable=False, comment="Название страны"),
        sa.Column("name_eng", sa.String(length=255), nullable=False, comment="Название страны ENG"),
        # Код страны
        sa.Column("iso_alpha_2", sa.String(length=2), nullable=False, comment="ISO Alpha-2"),
        sa.Column("iso_alpha_3", sa.String(length=3), nullable=False, comment="ISO Alpha-3"),
        sa.Column("iso_digits", sa.String(length=3), nullable=True, comment="ISO Digits"),
        # Местоположение
        sa.Column("latitude", sa.Float(), nullable=False, comment="Широта"),
        sa.Column("longitude", sa.Float(), nullable=False, comment="Долгота"),
        sa.Column(
            "geometry",
            Geometry(geometry_type="MULTIPOLYGON", srid=4326),
            nullable=True,
            comment="Геометрия страны в формате GeoJSON",
        ),
        # Характеристика страны
        sa.Column("language", sa.String(length=50), nullable=True, comment="Основной язык страны"),
        sa.Column("currency", sa.String(length=10), nullable=True, comment="Валюта страны"),
        sa.Column("timezone", sa.String(length=50), nullable=True, comment="Часовой пояс страны"),
        sa.Column("migration_policy", sa.Text(), nullable=True, comment="Краткое описание миграционной политики"),
        sa.Column("description", sa.Text(), nullable=True, comment="Описание страны"),
        sa.Column("population", sa.Integer(), nullable=True, comment="Население страны"),
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
        comment="Страны",
    )
    # Создаю индексы
    op.create_index("ix_country_id", "loc_country", ["id"])
    op.create_index("ix_country_name", "loc_country", ["name"])
    op.create_index("ix_country_name_eng", "loc_country", ["name_eng"])
    op.create_index("ix_country_iso_alpha_2", "loc_country", ["iso_alpha_2"])
    op.create_index("ix_country_iso_alpha_3", "loc_country", ["iso_alpha_3"])
    op.create_index("ix_country_iso_digits", "loc_country", ["iso_digits"])
    op.create_index("ix_country_latitude", "loc_country", ["latitude"])
    op.create_index("ix_country_longitude", "loc_country", ["longitude"])

    # Создаю уникальные ограничения
    op.create_unique_constraint("uq_country_name", "loc_country", ["name"])
    op.create_unique_constraint("uq_country_name_eng", "loc_country", ["name_eng"])
    op.create_unique_constraint("uq_country_iso_alpha_2", "loc_country", ["iso_alpha_2"])
    op.create_unique_constraint("uq_country_iso_alpha_3", "loc_country", ["iso_alpha_3"])
    op.create_unique_constraint("uq_country_iso_digits", "loc_country", ["iso_digits"])
    op.create_unique_constraint("uq_country_coordinates", "loc_country", ["latitude", "longitude"])

    # Создаю проверки
    op.create_check_constraint("ck_country_longitude_range", "loc_country", "longitude BETWEEN -180 AND 180")
    op.create_check_constraint("ck_country_latitude_range", "loc_country", "latitude BETWEEN -90 AND 90")


def delete_country():

    # Удаляю индексы, проверки для таблицы городов country
    op.drop_index("ix_country_id", table_name="loc_country")
    op.drop_index("ix_country_iso_alpha_2", table_name="loc_country")
    op.drop_index("ix_country_iso_alpha_3", table_name="loc_country")
    op.drop_index("ix_country_iso_digits", table_name="loc_country")
    op.drop_index("ix_country_name", table_name="loc_country")
    op.drop_index("ix_country_name_eng", table_name="loc_country")
    op.drop_index("ix_country_latitude", table_name="loc_country")
    op.drop_index("ix_country_longitude", table_name="loc_country")

    op.drop_constraint("uq_country_name", "loc_country", type_="unique")
    op.drop_constraint("uq_country_name_eng", "loc_country", type_="unique")
    op.drop_constraint("uq_country_iso_alpha_2", "loc_country", type_="unique")
    op.drop_constraint("uq_country_iso_alpha_3", "loc_country", type_="unique")
    op.drop_constraint("uq_country_iso_digits", "loc_country", type_="unique")
    op.drop_constraint("uq_country_coordinates", "loc_country", type_="unique")

    op.drop_constraint("ck_country_longitude_range", "loc_country", type_="check")
    op.drop_constraint("ck_country_latitude_range", "loc_country", type_="check")

    # Удаляю country
    op.drop_table("loc_country")

    # Удаляю последовательности
    op.execute("DROP SEQUENCE IF EXISTS loc_country_id_seq;")


def create_region():
    """Создаю таблицу loc_region"""

    # Создаём последовательность
    op.execute("CREATE SEQUENCE IF NOT EXISTS loc_region_id_seq START WITH 1 INCREMENT BY 1;")

    # Создаю таблицу
    op.create_table(
        "loc_region",
        # Идентификатор региона/страны
        sa.Column(
            "id",
            sa.Integer(),
            server_default=sa.text("nextval('loc_region_id_seq')"),
            primary_key=True,
            comment="ID региона",
        ),
        sa.Column(
            "country_id",
            sa.Integer(),
            sa.ForeignKey("loc_country.id", ondelete="CASCADE"),
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
        comment="Регионы",
    )
    # Создаю индексы
    op.create_index("ix_region_id", "loc_region", ["id"])
    op.create_index("ix_region_country_id", "loc_region", ["country_id"])
    op.create_index("ix_region_name", "loc_region", ["name"])
    op.create_index("ix_region_name_eng", "loc_region", ["name_eng"])

    # Создаю ограничения
    op.create_unique_constraint("uq_region_country_name", "loc_region", ["country_id", "name"])
    op.create_unique_constraint("uq_region_country_name_eng", "loc_region", ["country_id", "name_eng"])


def delete_region():

    # Удаляю индексы, проверки для таблицы городов region
    op.drop_index("ix_region_id", table_name="loc_region")
    op.drop_index("ix_region_country_id", table_name="loc_region")
    op.drop_index("ix_region_name", table_name="loc_region")
    op.drop_index("ix_region_name_eng", table_name="loc_region")

    op.drop_constraint("uq_region_name", "loc_region", type_="unique")
    op.drop_constraint("uq_region_name_eng", "loc_region", type_="unique")
    op.drop_constraint("uq_region_country_name", "loc_region", type_="unique")
    op.drop_constraint("uq_region_country_name_eng", "loc_region", type_="unique")

    # Удаляю таблицу region
    op.drop_table("loc_region")

    # Удаляю последовательности
    op.execute("DROP SEQUENCE IF EXISTS loc_region_id_seq;")


def create_city():
    """Создаю таблицу loc_city"""

    # Создаём последовательность
    op.execute("CREATE SEQUENCE IF NOT EXISTS loc_city_id_seq START WITH 1 INCREMENT BY 1;")

    # Создаю таблицу
    op.create_table(
        "loc_city",
        # Идентификатор города
        sa.Column(
            "id",
            sa.Integer(),
            server_default=sa.text("nextval('loc_city_id_seq')"),
            primary_key=True,
            comment="ID города",
        ),
        sa.Column(
            "country_id",
            sa.Integer(),
            sa.ForeignKey("loc_country.id", ondelete="CASCADE"),
            nullable=False,
            comment="ID страны",
        ),
        sa.Column(
            "region_id",
            sa.Integer(),
            sa.ForeignKey("loc_region.id", ondelete="CASCADE"),
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
        comment="Города",
    )
    # Создаю индексы
    op.create_index("ix_city_id", "loc_city", ["id"])
    op.create_index("ix_city_country_id", "loc_city", ["country_id"])
    op.create_index("ix_city_region_id", "loc_city", ["region_id"])
    op.create_index("ix_city_name", "loc_city", ["name"])
    op.create_index("ix_city_name_eng", "loc_city", ["name_eng"])
    op.create_index("ix_city_latitude", "loc_city", ["latitude"])
    op.create_index("ix_city_longitude", "loc_city", ["longitude"])
    # Создаю уникальные ограничения
    op.create_unique_constraint("uq_city_country_name", "loc_city", ["country_id", "name"])
    op.create_unique_constraint("uq_city_country_name_eng", "loc_city", ["country_id", "name_eng"])
    op.create_unique_constraint("uq_city_coordinates", "loc_city", ["latitude", "longitude"])
    # Создаю проверки
    op.create_check_constraint("ck_city_latitude_range", "loc_city", "latitude BETWEEN -90 AND 90")
    op.create_check_constraint("ck_city_longitude_range", "loc_city", "longitude BETWEEN -180 AND 180")

    # Создаю уникальный индекс
    op.create_index(
        "uq_city_capital_per_country",
        "loc_city",
        ["country_id"],
        postgresql_where=sa.text("is_capital IS TRUE"),
    )


def delete_city():
    """Удаление таблицы loc_city"""

    # Удаляю уникальные индексы
    op.drop_index("uq_city_capital_per_country", table_name="loc_city")

    # Удаляю индексы
    op.drop_index("ix_city_longitude", table_name="loc_city")
    op.drop_index("ix_city_latitude", table_name="loc_city")
    op.drop_index("ix_city_name_eng", table_name="loc_city")
    op.drop_index("ix_city_name", table_name="loc_city")
    op.drop_index("ix_city_region_id", table_name="loc_city")
    op.drop_index("ix_city_country_id", table_name="loc_city")
    op.drop_index("ix_city_id", table_name="loc_city")

    op.drop_constraint("uq_city_coordinates", "loc_city", type_="unique")
    op.drop_constraint("uq_city_country_name_eng", "loc_city", type_="unique")
    op.drop_constraint("uq_city_country_name", "loc_city", type_="unique")
    op.drop_constraint("ck_city_latitude_range", "loc_city", type_="check")
    op.drop_constraint("ck_city_longitude_range", "loc_city", type_="check")

    # Удаляю таблицу
    op.drop_table("loc_city")

    # Удаляю последовательности
    op.execute("DROP SEQUENCE IF EXISTS loc_city_id_seq;")


#
#
# ==================== Миграция создания и удаления таблиц ====================
def upgrade() -> None:

    # Создаём расширение PostGIS, если оно ещё не установлено
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis;")

    create_contry()
    create_region()
    create_city()


def downgrade():

    # Удаляем расширение PostGIS
    op.execute("DROP EXTENSION IF EXISTS postgis;")

    delete_city()
    delete_region()
    delete_country()
