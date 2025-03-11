"""Initial migration

Revision ID: da8ca8207093
Revises: 
Create Date: 2025-03-10 18:06:26.652349

"""
from alembic import op
import sqlalchemy as sa
import geoalchemy2
from geoalchemy2 import Geometry

# revision identifiers, used by Alembic.
revision = 'da8ca8207093'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('adaptationtarget',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('target', sa.String(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_adaptationtarget_target'), 'adaptationtarget', ['target'], unique=True)
    op.create_table('apiversion',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_apiversion_version'), 'apiversion', ['version'], unique=True)
    op.create_table('impact_intensity',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('intensity', sa.String(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_impact_intensity_intensity'), 'impact_intensity', ['intensity'], unique=True)
    op.create_table('impact_unit',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('unit', sa.String(), nullable=False),
    sa.Column('description', sa.String(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_impact_unit_description'), 'impact_unit', ['description'], unique=False)
    op.create_index(op.f('ix_impact_unit_unit'), 'impact_unit', ['unit'], unique=True)
    op.create_geospatial_table('naturebasedsolution',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('definition', sa.String(), nullable=False),
    sa.Column('cobenefits', sa.String(), nullable=False),
    sa.Column('specificdetails', sa.String(), nullable=False),
    sa.Column('location', sa.String(), nullable=False),
    sa.Column('geometry', Geometry(srid=4326, spatial_index=False, from_text='ST_GeomFromEWKT', name='geometry'), nullable=True, spatial_index=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_geospatial_index('idx_geo_data_geometry', 'naturebasedsolution', ['geometry'], unique=False, postgresql_using='gist', postgresql_ops={})
    op.create_geospatial_index('idx_naturebasedsolution_geometry', 'naturebasedsolution', ['geometry'], unique=False, postgresql_using='gist', postgresql_ops={})
    op.create_index(op.f('ix_naturebasedsolution_cobenefits'), 'naturebasedsolution', ['cobenefits'], unique=False)
    op.create_index(op.f('ix_naturebasedsolution_definition'), 'naturebasedsolution', ['definition'], unique=False)
    op.create_index(op.f('ix_naturebasedsolution_location'), 'naturebasedsolution', ['location'], unique=False)
    op.create_index(op.f('ix_naturebasedsolution_name'), 'naturebasedsolution', ['name'], unique=True)
    op.create_index(op.f('ix_naturebasedsolution_specificdetails'), 'naturebasedsolution', ['specificdetails'], unique=False)
    op.create_table('impact',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('magnitude', sa.Float(), nullable=False),
    sa.Column('intensity_id', sa.Integer(), nullable=False),
    sa.Column('unit_id', sa.Integer(), nullable=False),
    sa.Column('solution_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['intensity_id'], ['impact_intensity.id'], ),
    sa.ForeignKeyConstraint(['solution_id'], ['naturebasedsolution.id'], ),
    sa.ForeignKeyConstraint(['unit_id'], ['impact_unit.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_impact_magnitude'), 'impact', ['magnitude'], unique=False)
    op.create_table('nbs_target_assoc',
    sa.Column('nbs_id', sa.Integer(), nullable=False),
    sa.Column('target_id', sa.Integer(), nullable=False),
    sa.Column('value', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['nbs_id'], ['naturebasedsolution.id'], ),
    sa.ForeignKeyConstraint(['target_id'], ['adaptationtarget.id'], ),
    sa.PrimaryKeyConstraint('nbs_id', 'target_id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('nbs_target_assoc')
    op.drop_index(op.f('ix_impact_magnitude'), table_name='impact')
    op.drop_table('impact')
    op.drop_index(op.f('ix_naturebasedsolution_specificdetails'), table_name='naturebasedsolution')
    op.drop_index(op.f('ix_naturebasedsolution_name'), table_name='naturebasedsolution')
    op.drop_index(op.f('ix_naturebasedsolution_location'), table_name='naturebasedsolution')
    op.drop_index(op.f('ix_naturebasedsolution_definition'), table_name='naturebasedsolution')
    op.drop_index(op.f('ix_naturebasedsolution_cobenefits'), table_name='naturebasedsolution')
    op.drop_geospatial_index('idx_naturebasedsolution_geometry', table_name='naturebasedsolution', postgresql_using='gist', column_name='geometry')
    op.drop_geospatial_index('idx_geo_data_geometry', table_name='naturebasedsolution', postgresql_using='gist', column_name='geometry')
    op.drop_geospatial_table('naturebasedsolution')
    op.drop_index(op.f('ix_impact_unit_unit'), table_name='impact_unit')
    op.drop_index(op.f('ix_impact_unit_description'), table_name='impact_unit')
    op.drop_table('impact_unit')
    op.drop_index(op.f('ix_impact_intensity_intensity'), table_name='impact_intensity')
    op.drop_table('impact_intensity')
    op.drop_index(op.f('ix_apiversion_version'), table_name='apiversion')
    op.drop_table('apiversion')
    op.drop_index(op.f('ix_adaptationtarget_target'), table_name='adaptationtarget')
    op.drop_table('adaptationtarget')
    # ### end Alembic commands ###
