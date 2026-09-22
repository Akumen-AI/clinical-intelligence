"""Add refresh_tokens table

Revision ID: c70d8c54004c
Revises: 2d864cfc900a
Create Date: 2026-09-21 22:41:31.510021

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c70d8c54004c'
down_revision = '2d864cfc900a'
branch_labels = None
depends_on = None


def upgrade() -> None:
    try:
        op.create_table(
            'refresh_tokens',
            sa.Column('id', sa.UUID(), nullable=False),
            sa.Column('user_id', sa.UUID(), nullable=False),
            sa.Column('token_jti', sa.String(length=255), nullable=False),
            sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('revoked', sa.Boolean(), nullable=False, default=False),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_refresh_tokens_token_jti'), 'refresh_tokens', ['token_jti'], unique=True)
    except Exception:
        pass


def downgrade() -> None:
    try:
        op.drop_index(op.f('ix_refresh_tokens_token_jti'), table_name='refresh_tokens')
        op.drop_table('refresh_tokens')
    except Exception:
        pass
