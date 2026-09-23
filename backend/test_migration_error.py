import sqlalchemy as sa
from sqlalchemy import create_engine
from alembic.migration import MigrationContext
from alembic.operations import Operations

engine = create_engine("sqlite:///:memory:")
ctx = MigrationContext.configure(engine.connect())
op = Operations(ctx)

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
    print("Table created successfully!")
except Exception as e:
    import traceback
    traceback.print_exc()
