"""add_department_completeness_settings

Revision ID: 007_add_dept_completeness
Revises: 006_add_patient_duplicate_flags
Create Date: 2026-09-14 17:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '007_add_dept_completeness'
down_revision = '006_add_patient_duplicate_flags'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        dept_id_col = sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()'))
        setting_id_col = sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()'))
        setting_dept_id_col = sa.Column('department_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('departments.id', ondelete='CASCADE'), nullable=False, unique=True)
        setting_user_id_col = sa.Column('updated_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True)
    else:
        dept_id_col = sa.Column('id', sa.String(length=36), primary_key=True)
        setting_id_col = sa.Column('id', sa.String(length=36), primary_key=True)
        setting_dept_id_col = sa.Column('department_id', sa.String(length=36), sa.ForeignKey('departments.id', ondelete='CASCADE'), nullable=False, unique=True)
        setting_user_id_col = sa.Column('updated_by', sa.String(length=36), sa.ForeignKey('users.id'), nullable=True)

    tables = sa.inspect(bind).get_table_names()
    if 'departments' not in tables:
        op.create_table(
            'departments',
            dept_id_col,
            sa.Column('name', sa.String(length=128), nullable=False, unique=True)
        )

    if 'department_completeness_settings' not in tables:
        op.create_table(
            'department_completeness_settings',
            setting_id_col,
            setting_dept_id_col,
            sa.Column('enabled', sa.Boolean(), nullable=False, server_default=sa.text('TRUE')),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
            setting_user_id_col,
        )


def downgrade() -> None:
    op.drop_table('department_completeness_settings')
    bind = op.get_bind()
    tables = sa.inspect(bind).get_table_names()
    if 'departments' in tables:
        op.drop_table('departments')
