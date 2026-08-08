"""Initialize PostGIS extension

Revision ID: 20260808_0000
Revises: 
Create Date: 2026-08-08 00:00:00.000000

This migration MUST run first to enable PostGIS before creating
geometry columns.
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '20260808_0000'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Enable PostGIS extension."""
    # Enable PostGIS extension (requires superuser or rds_superuser role)
    op.execute('CREATE EXTENSION IF NOT EXISTS postgis')
    
    # Verify PostGIS version (optional but useful for debugging)
    op.execute('SELECT PostGIS_Version()')


def downgrade() -> None:
    """Disable PostGIS extension."""
    # WARNING: This will cascade delete all geometry columns!
    # Only run this in development environments.
    op.execute('DROP EXTENSION IF EXISTS postgis CASCADE')
