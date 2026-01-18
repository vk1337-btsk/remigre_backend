"""create data_professions table

Revision ID: 27f9a46b25f7
Revises: b898e1587fb7
Create Date: 2025-12-22 17:49:16.631822

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "27f9a46b25f7"
down_revision: Union[str, Sequence[str], None] = "b898e1587fb7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "data_professions",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False, comment="ID"),
        # Основные данные
        sa.Column("name", sa.String(length=255), nullable=False, comment="Название"),
        sa.Column("name_eng", sa.String(length=255), nullable=False, comment="Название ENG"),
        sa.Column("description", sa.Text(), nullable=True, comment="Описание"),
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
        comment="Справочник профессий",
    )

    # Индекс (если хочешь соответствие модели с index=True)
    op.create_index("ix_data_professions_id", "data_professions", ["id"])


def downgrade() -> None:

    op.drop_index("ix_data_professions_id", table_name="data_professions")
    op.drop_table("data_professions")
