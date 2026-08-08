"""Create initial schema with all tables

Revision ID: 20260808_0001
Revises: 20260808_0000
Create Date: 2026-08-08 00:01:00.000000

Creates all tables for the Palestine Land Valuation platform:
- users: User accounts and authentication
- parcels: Land parcels with valuation data
- saved_parcels: User's saved parcels (privacy-by-default)
- geopolitical_boundaries: Oslo Accords Areas A/B/C
- zoning_plans: GeoMOLG master plan data
- comps: Comparable sales for valuation engine
- spatial_data_changelog: Audit trail for ETL imports
"""
from typing import Sequence, Union

import sqlalchemy as sa
import geoalchemy2
from alembic import op


# revision identifiers, used by Alembic.
revision: str = '20260808_0001'
down_revision: Union[str, None] = '20260808_0000'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all tables with PostGIS geometry columns."""
    
    # ─── Users Table ───────────────────────────────────────────────
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('hashed_password', sa.String(), nullable=False),
        sa.Column('full_name', sa.String(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    
    # ─── Parcels Table ─────────────────────────────────────────────
    op.create_table(
        'parcels',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('geometry', geoalchemy2.types.Geometry(
            geometry_type='POLYGON',
            srid=4326,
            from_text='ST_GeomFromEWKT',
            name='geometry'
        ), nullable=False),
        sa.Column('governorate', sa.String(length=100), nullable=False),
        sa.Column('area_sqm', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('oslo_classification', sa.String(length=10), nullable=True),
        sa.Column('zoning_code', sa.String(length=50), nullable=True),
        sa.Column('zoning_description', sa.String(length=255), nullable=True),
        sa.Column('valuation_min_per_sqm', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('valuation_max_per_sqm', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('valuation_confidence', sa.Numeric(precision=4, scale=3), nullable=True),
        sa.Column('valuation_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('comp_count', sa.Integer(), nullable=True),
        sa.Column('degrees_of_freedom', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_parcels_id'), 'parcels', ['id'], unique=False)
    op.create_index(op.f('ix_parcels_governorate'), 'parcels', ['governorate'], unique=False)
    op.create_index(op.f('ix_parcels_oslo_classification'), 'parcels', ['oslo_classification'], unique=False)
    op.create_index(op.f('ix_parcels_zoning_code'), 'parcels', ['zoning_code'], unique=False)
    
    # GiST spatial index for parcels
    op.execute('CREATE INDEX idx_parcel_geometry_gist ON parcels USING GIST (geometry)')
    
    # ─── Saved Parcels Table ───────────────────────────────────────
    op.create_table(
        'saved_parcels',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('parcel_id', sa.Integer(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('saved_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['parcel_id'], ['parcels.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_saved_parcels_id'), 'saved_parcels', ['id'], unique=False)
    op.create_index(op.f('ix_saved_parcels_user_id'), 'saved_parcels', ['user_id'], unique=False)
    op.create_index(op.f('ix_saved_parcels_parcel_id'), 'saved_parcels', ['parcel_id'], unique=False)
    op.create_index('idx_saved_parcel_user_parcel_unique', 'saved_parcels', ['user_id', 'parcel_id'], unique=True)
    
    # ─── Geopolitical Boundaries Table ─────────────────────────────
    op.create_table(
        'geopolitical_boundaries',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('geometry', geoalchemy2.types.Geometry(
            geometry_type='MULTIPOLYGON',
            srid=4326,
            from_text='ST_GeomFromEWKT',
            name='geometry'
        ), nullable=False),
        sa.Column('classification', sa.String(length=10), nullable=False),
        sa.Column('governorate', sa.String(length=100), nullable=False),
        sa.Column('source_version', sa.String(length=255), nullable=False),
        sa.Column('effective_date', sa.Date(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        comment='Oslo classification: A, B, or C'
    )
    op.create_index(op.f('ix_geopolitical_boundaries_id'), 'geopolitical_boundaries', ['id'], unique=False)
    op.create_index(op.f('ix_geopolitical_boundaries_classification'), 'geopolitical_boundaries', ['classification'], unique=False)
    op.create_index(op.f('ix_geopolitical_boundaries_governorate'), 'geopolitical_boundaries', ['governorate'], unique=False)
    op.create_index('idx_geopolitical_gov_class', 'geopolitical_boundaries', ['governorate', 'classification'], unique=False)
    
    # GiST spatial index for geopolitical boundaries
    op.execute('CREATE INDEX idx_geopolitical_geometry_gist ON geopolitical_boundaries USING GIST (geometry)')
    
    # ─── Zoning Plans Table ────────────────────────────────────────
    op.create_table(
        'zoning_plans',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('geometry', geoalchemy2.types.Geometry(
            geometry_type='MULTIPOLYGON',
            srid=4326,
            from_text='ST_GeomFromEWKT',
            name='geometry'
        ), nullable=False),
        sa.Column('governorate', sa.String(length=100), nullable=False),
        sa.Column('locality', sa.String(length=100), nullable=False),
        sa.Column('zoning_code', sa.String(length=50), nullable=False),
        sa.Column('zoning_description', sa.Text(), nullable=True),
        sa.Column('max_building_height', sa.Integer(), nullable=True),
        sa.Column('max_floor_area_ratio', sa.String(length=10), nullable=True),
        sa.Column('source_version', sa.String(length=255), nullable=False),
        sa.Column('effective_date', sa.Date(), nullable=False),
        sa.Column('plan_approval_date', sa.Date(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_zoning_plans_id'), 'zoning_plans', ['id'], unique=False)
    op.create_index(op.f('ix_zoning_plans_governorate'), 'zoning_plans', ['governorate'], unique=False)
    op.create_index(op.f('ix_zoning_plans_locality'), 'zoning_plans', ['locality'], unique=False)
    op.create_index('idx_zoning_code', 'zoning_plans', ['zoning_code'], unique=False)
    op.create_index('idx_zoning_gov_locality', 'zoning_plans', ['governorate', 'locality'], unique=False)
    
    # GiST spatial index for zoning plans
    op.execute('CREATE INDEX idx_zoning_geometry_gist ON zoning_plans USING GIST (geometry)')
    
    # ─── Comps Table ───────────────────────────────────────────────
    op.create_table(
        'comps',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('geometry', geoalchemy2.types.Geometry(
            geometry_type='POINT',
            srid=4326,
            from_text='ST_GeomFromEWKT',
            name='geometry'
        ), nullable=False),
        sa.Column('governorate', sa.String(length=100), nullable=False),
        sa.Column('locality', sa.String(length=100), nullable=False),
        sa.Column('sale_date', sa.Date(), nullable=False),
        sa.Column('price_ils', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('area_sqm', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('price_per_sqm', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('oslo_classification', sa.String(length=10), nullable=False),
        sa.Column('zoning_code', sa.String(length=50), nullable=True),
        sa.Column('distance_to_road_m', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('distance_to_city_center_m', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('has_water_access', sa.Boolean(), nullable=True),
        sa.Column('has_electricity_access', sa.Boolean(), nullable=True),
        sa.Column('slope_category', sa.String(length=20), nullable=True),
        sa.Column('source', sa.String(length=255), nullable=False),
        sa.Column('source_confidence', sa.Integer(), nullable=False),
        sa.Column('verified_by', sa.String(length=255), nullable=True),
        sa.Column('verification_date', sa.Date(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_comps_id'), 'comps', ['id'], unique=False)
    op.create_index(op.f('ix_comps_governorate'), 'comps', ['governorate'], unique=False)
    op.create_index(op.f('ix_comps_locality'), 'comps', ['locality'], unique=False)
    op.create_index(op.f('ix_comps_sale_date'), 'comps', ['sale_date'], unique=False)
    op.create_index(op.f('ix_comps_oslo_classification'), 'comps', ['oslo_classification'], unique=False)
    op.create_index(op.f('ix_comps_zoning_code'), 'comps', ['zoning_code'], unique=False)
    op.create_index(op.f('ix_comps_price_per_sqm'), 'comps', ['price_per_sqm'], unique=False)
    op.create_index('idx_comp_gov_date', 'comps', ['governorate', sa.text('sale_date DESC')], unique=False)
    
    # GiST spatial index for comps
    op.execute('CREATE INDEX idx_comp_geometry_gist ON comps USING GIST (geometry)')
    
    # ─── Spatial Data Changelog Table ──────────────────────────────
    op.create_table(
        'spatial_data_changelog',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('table_name', sa.String(length=100), nullable=False),
        sa.Column('operation', sa.String(length=20), nullable=False),
        sa.Column('source_name', sa.String(length=100), nullable=False),
        sa.Column('source_version', sa.String(length=255), nullable=False),
        sa.Column('records_affected', sa.Integer(), nullable=False),
        sa.Column('import_method', sa.String(length=100), nullable=False),
        sa.Column('executed_by', sa.String(length=100), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('executed_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_spatial_data_changelog_id'), 'spatial_data_changelog', ['id'], unique=False)
    op.create_index(op.f('ix_spatial_data_changelog_table_name'), 'spatial_data_changelog', ['table_name'], unique=False)
    op.create_index(op.f('ix_spatial_data_changelog_source_name'), 'spatial_data_changelog', ['source_name'], unique=False)
    op.create_index(op.f('ix_spatial_data_changelog_executed_at'), 'spatial_data_changelog', ['executed_at'], unique=False)


def downgrade() -> None:
    """Drop all tables."""
    op.drop_table('spatial_data_changelog')
    op.drop_table('comps')
    op.drop_table('zoning_plans')
    op.drop_table('geopolitical_boundaries')
    op.drop_table('saved_parcels')
    op.drop_table('parcels')
    op.drop_table('users')
