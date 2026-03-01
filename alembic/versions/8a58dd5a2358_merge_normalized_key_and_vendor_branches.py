"""merge normalized_key and vendor branches

Revision ID: 8a58dd5a2358
Revises: a1b2c3d4e5f6, a7c9d1e3f5b7
Create Date: 2026-03-01 06:24:30.569036

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8a58dd5a2358'
down_revision: Union[str, Sequence[str], None] = ('a1b2c3d4e5f6', 'a7c9d1e3f5b7')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
