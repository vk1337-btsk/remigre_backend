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


def upgrade() -> None:

    # Создаю таблицу со странами
    op.create_table(
        "country",
        sa.Column("id", sa.Integer(), nullable=False, comment="ID страны"),
        sa.Column("name", sa.String(length=255), nullable=False, comment="Название страны"),
        sa.Column("name_eng", sa.String(length=255), nullable=False, comment="Название страны ENG"),
        sa.Column("iso_code", sa.String(length=10), nullable=False, comment="Код страны ISO 3166"),
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
        comment="Таблица стран и данными о них",
    )
    op.create_index(op.f("ix_country_id"), "country", ["id"], unique=False)
    op.create_index(op.f("ix_country_name"), "country", ["name"], unique=True)
    op.create_index(op.f("ix_country_name_eng"), "country", ["name_eng"], unique=True)
    op.create_index(op.f("ix_country_iso_code"), "country", ["iso_code"], unique=True)

    # Создаю таблицу с городами
    op.create_table(
        "city",
        sa.Column("id", sa.Integer(), nullable=False, comment="ID города"),
        sa.Column("country_id", sa.Integer(), nullable=False, comment="ID страны"),
        sa.Column("name", sa.String(length=255), nullable=False, comment="Название города"),
        sa.Column("name_eng", sa.String(length=255), nullable=False, comment="Название города ENG"),
        sa.Column("latitude", sa.Float(), nullable=False, comment="Широта"),
        sa.Column("longitude", sa.Float(), nullable=False, comment="Долгота"),
        sa.Column("timezone", sa.String(length=100), nullable=True, comment="Часовой пояс"),
        sa.Column("region", sa.String(length=255), nullable=True, comment="Регион"),
        sa.Column("is_capital", sa.Boolean(), nullable=False, comment="Столица"),
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
        sa.ForeignKeyConstraint(["country_id"], ["country.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("latitude", "longitude", name="uq_city_coordinates"),
        comment="Таблица городов и данными о них",
    )
    op.create_index(op.f("ix_city_id"), "city", ["id"], unique=False)
    op.create_index(op.f("ix_city_country_id"), "city", ["country_id"], unique=False)
    op.create_index(op.f("ix_city_name"), "city", ["name"], unique=False)
    op.create_index(op.f("ix_city_name_eng"), "city", ["name_eng"], unique=False)
    op.create_index(op.f("ix_city_latitude"), "city", ["latitude"], unique=False)
    op.create_index(op.f("ix_city_longitude"), "city", ["longitude"], unique=False)


def downgrade() -> None:

    # Удаляю таблицу с городами
    op.drop_index(op.f("ix_city_id"), table_name="city")
    op.drop_index(op.f("ix_city_country_id"), table_name="city")
    op.drop_index(op.f("ix_city_name"), table_name="city")
    op.drop_index(op.f("ix_city_name_eng"), table_name="city")
    op.drop_index(op.f("ix_city_longitude"), table_name="city")
    op.drop_index(op.f("ix_city_latitude"), table_name="city")
    op.drop_table("city")

    # Удаляю таблицу со странами
    op.drop_index(op.f("ix_country_id"), table_name="country")
    op.drop_index(op.f("ix_country_name"), table_name="country")
    op.drop_index(op.f("ix_country_name_eng"), table_name="country")
    op.drop_index(op.f("ix_country_iso_code"), table_name="country")
    op.drop_table("country")
