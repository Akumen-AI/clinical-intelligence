"""Add UserRole enum

Revision ID: 28896420340f
Revises: d84d7da68980
Create Date: 2026-08-18 12:19:39.332200

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '28896420340f'
down_revision = 'd84d7da68980'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Normalize existing roles to closest enum members
    op.execute("UPDATE users SET role = 'doctor' WHERE LOWER(role) LIKE '%doctor%' OR LOWER(role) LIKE '%dr%'")
    op.execute("UPDATE users SET role = 'nurse' WHERE LOWER(role) LIKE '%nurse%' OR LOWER(role) LIKE '%rn%'")
    op.execute("UPDATE users SET role = 'hospital_admin' WHERE LOWER(role) LIKE '%admin%' OR LOWER(role) LIKE '%hospital%'")
    op.execute("UPDATE users SET role = 'department_head' WHERE LOWER(role) LIKE '%head%' OR LOWER(role) LIKE '%dept%'")
    op.execute("UPDATE users SET role = 'it' WHERE LOWER(role) LIKE '%it%' OR LOWER(role) LIKE '%tech%'")
    op.execute("UPDATE users SET role = 'compliance' WHERE LOWER(role) LIKE '%compliance%' OR LOWER(role) LIKE '%legal%'")
    
    # Default anything unrecognized to 'nurse'
    op.execute("UPDATE users SET role = 'nurse' WHERE role NOT IN ('doctor', 'nurse', 'hospital_admin', 'department_head', 'it', 'compliance')")

    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.alter_column('role',
               existing_type=sa.String(length=50),
               type_=sa.Enum('doctor', 'nurse', 'hospital_admin', 'department_head', 'it', 'compliance', name='userrole'),
               existing_nullable=False,
               server_default='nurse')

def downgrade() -> None:
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.alter_column('role',
               existing_type=sa.Enum('doctor', 'nurse', 'hospital_admin', 'department_head', 'it', 'compliance', name='userrole'),
               type_=sa.String(length=50),
               existing_nullable=False,
               server_default='nurse')
