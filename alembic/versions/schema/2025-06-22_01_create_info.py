"""Создание таблицы info

Revision ID: 9f7bc9e202b3
Revises:
Create Date: 2025-06-22 12:45:10.433971

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "9f7bc9e202b3"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    # Создаю таблицу с данными сайта
    op.create_table(
        "info",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True, comment="ID записи"),
        sa.Column("slug", sa.String(), nullable=False, comment="Название раздела"),
        sa.Column("description", sa.Text(), nullable=False, comment="Описание раздела"),
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
        comment="Таблица с данными для заполнения сайта",
    )
    op.create_index(op.f("ix_info_id"), "info", ["id"], unique=False)
    op.create_index(op.f("ix_info_slug"), "info", ["slug"], unique=True)


def downgrade() -> None:

    # Удаляем таблицу с данными сайта
    op.drop_index(op.f("ix_info_id"), table_name="info")
    op.drop_index(op.f("ix_info_slug"), table_name="info")
    op.drop_table("info")
