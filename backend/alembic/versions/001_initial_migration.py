"""Initial migration - create financial ledger tables

Revision ID: 001
Revises: 
Create Date: 2026-01-12 17:50:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID


# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create ledger_entries table
    op.create_table(
        'ledger_entries',
        sa.Column('id', UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', sa.String(length=255), nullable=False),
        sa.Column('entry_type', sa.Enum('CREDIT', 'DEBIT', 'REVERSAL', name='entrytype'), nullable=False),
        sa.Column('amount_cents', sa.BigInteger(), nullable=False),
        sa.Column('reward_id', sa.String(length=255), nullable=True),
        sa.Column('reward_status', sa.Enum('PENDING', 'CONFIRMED', 'PAID', 'REVERSED', name='rewardstatus'), nullable=True),
        sa.Column('idempotency_key', sa.String(length=255), nullable=False),
        sa.Column('related_entry_id', UUID(as_uuid=True), nullable=True),
        sa.Column('extra_data', JSONB(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.CheckConstraint('amount_cents > 0', name='positive_amount'),
        sa.ForeignKeyConstraint(['related_entry_id'], ['ledger_entries.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('idempotency_key')
    )
    op.create_index('idx_reward', 'ledger_entries', ['reward_id', 'reward_status'], unique=False)
    op.create_index('idx_user_created', 'ledger_entries', ['user_id', 'created_at'], unique=False)
    op.create_index(op.f('ix_ledger_entries_created_at'), 'ledger_entries', ['created_at'], unique=False)
    op.create_index(op.f('ix_ledger_entries_idempotency_key'), 'ledger_entries', ['idempotency_key'], unique=True)
    op.create_index(op.f('ix_ledger_entries_reward_id'), 'ledger_entries', ['reward_id'], unique=False)
    op.create_index(op.f('ix_ledger_entries_user_id'), 'ledger_entries', ['user_id'], unique=False)
    
    # Create user_balances table
    op.create_table(
        'user_balances',
        sa.Column('user_id', sa.String(length=255), nullable=False),
        sa.Column('balance_cents', sa.BigInteger(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.CheckConstraint('balance_cents >= 0', name='non_negative_balance'),
        sa.PrimaryKeyConstraint('user_id')
    )
    
    # Create referral_rules table
    op.create_table(
        'referral_rules',
        sa.Column('id', UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('rule_json', JSONB(), nullable=False),
        sa.Column('is_active', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create idempotency_records table
    op.create_table(
        'idempotency_records',
        sa.Column('idempotency_key', sa.String(length=255), nullable=False),
        sa.Column('request_hash', sa.String(length=64), nullable=False),
        sa.Column('response_data', JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('idempotency_key')
    )
    op.create_index(op.f('ix_idempotency_records_created_at'), 'idempotency_records', ['created_at'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_idempotency_records_created_at'), table_name='idempotency_records')
    op.drop_table('idempotency_records')
    op.drop_table('referral_rules')
    op.drop_table('user_balances')
    op.drop_index(op.f('ix_ledger_entries_user_id'), table_name='ledger_entries')
    op.drop_index(op.f('ix_ledger_entries_reward_id'), table_name='ledger_entries')
    op.drop_index(op.f('ix_ledger_entries_idempotency_key'), table_name='ledger_entries')
    op.drop_index(op.f('ix_ledger_entries_created_at'), table_name='ledger_entries')
    op.drop_index('idx_user_created', table_name='ledger_entries')
    op.drop_index('idx_reward', table_name='ledger_entries')
    op.drop_table('ledger_entries')
    op.execute('DROP TYPE rewardstatus')
    op.execute('DROP TYPE entrytype')
