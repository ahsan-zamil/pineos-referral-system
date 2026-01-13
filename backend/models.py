"""
SQLAlchemy models for the financial ledger system.

Key Design Principles:
1. Immutability: ledger_entries are append-only, never updated or deleted
2. Auditability: Every transaction is recorded with full metadata
3. ACID compliance: All operations use database transactions
4. Idempotency: Duplicate requests are detected via idempotency_key
"""
from sqlalchemy import (
    Column, String, Integer, BigInteger, Enum, DateTime, 
    ForeignKey, Index, CheckConstraint, UniqueConstraint, Text
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
import uuid
from database import Base


class EntryType(str, enum.Enum):
    """Types of ledger entries."""
    CREDIT = "credit"
    DEBIT = "debit"
    REVERSAL = "reversal"


class RewardStatus(str, enum.Enum):
    """Lifecycle states for rewards."""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PAID = "paid"
    REVERSED = "reversed"


class LedgerEntry(Base):
    """
    Immutable financial ledger entries.
    
    Design Notes:
    - Immutable: Once created, entries are never modified
    - amount_cents: Stored as integer to avoid floating-point errors
    - idempotency_key: Ensures duplicate requests don't create duplicate entries
    - related_entry_id: Links reversals to original entries
    - extra_data: Flexible JSONB for audit trail and context
    """
    __tablename__ = "ledger_entries"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(255), nullable=False, index=True)
    entry_type = Column(Enum(EntryType), nullable=False)
    amount_cents = Column(BigInteger, nullable=False)  # Money in cents to avoid float issues
    
    # Reward tracking
    reward_id = Column(String(255), nullable=True, index=True)
    reward_status = Column(Enum(RewardStatus), nullable=True)
    
    # Idempotency and relationships
    idempotency_key = Column(String(255), nullable=False, unique=True, index=True)
    related_entry_id = Column(UUID(as_uuid=True), ForeignKey("ledger_entries.id"), nullable=True)
    
    # Audit data (renamed from 'metadata' to avoid SQLAlchemy reserved attribute)
    extra_data = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    
    # Relationships
    related_entry = relationship("LedgerEntry", remote_side=[id], backref="reversals")
    
    # Constraints
    __table_args__ = (
        CheckConstraint("amount_cents > 0", name="positive_amount"),
        Index("idx_user_created", "user_id", "created_at"),
        Index("idx_reward", "reward_id", "reward_status"),
    )
    
    def __repr__(self):
        return f"<LedgerEntry {self.entry_type} user={self.user_id} amount={self.amount_cents}>"


class UserBalance(Base):
    """
    Materialized view of user balances.
    
    Design Notes:
    - Updated atomically with ledger entries in the same transaction
    - Provides O(1) balance lookups instead of calculating from ledger
    - version: Optimistic locking to prevent race conditions
    """
    __tablename__ = "user_balances"
    
    user_id = Column(String(255), primary_key=True)
    balance_cents = Column(BigInteger, nullable=False, default=0)
    version = Column(Integer, nullable=False, default=1)  # Optimistic locking
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        CheckConstraint("balance_cents >= 0", name="non_negative_balance"),
    )
    
    def __repr__(self):
        return f"<UserBalance user={self.user_id} balance={self.balance_cents}>"


class ReferralRule(Base):
    """
    Rule definitions for the referral engine.
    
    Design Notes:
    - rule_json: Full rule definition in JSON format
    - is_active: Allows enabling/disabling rules without deletion
    """
    __tablename__ = "referral_rules"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    rule_json = Column(JSONB, nullable=False)
    is_active = Column(Integer, nullable=False, default=1)  # 1 = active, 0 = inactive
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<ReferralRule {self.name} active={self.is_active}>"


class IdempotencyRecord(Base):
    """
    Track idempotency keys to prevent duplicate operations.
    
    Design Notes:
    - Separate table for faster lookups
    - response_data: Cached response for repeated requests
    - expires_at: Allow cleanup of old records
    """
    __tablename__ = "idempotency_records"
    
    idempotency_key = Column(String(255), primary_key=True)
    request_hash = Column(String(64), nullable=False)  # Hash of request body
    response_data = Column(JSONB, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    
    def __repr__(self):
        return f"<IdempotencyRecord key={self.idempotency_key}>"
