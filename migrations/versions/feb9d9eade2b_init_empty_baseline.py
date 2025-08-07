"""init empty baseline

Revision ID: feb9d9eade2b
Revises:
Create Date: 2025-08-07 01:13:55.178371

"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "feb9d9eade2b"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # No-op baseline
    pass


def downgrade() -> None:
    """Downgrade schema."""
    # No-op baseline
    pass
