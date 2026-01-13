"""Pydantic schemas for API request/response validation."""
from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from datetime import datetime
from models import EntryType, RewardStatus
import uuid


class LedgerCreditRequest(BaseModel):
    """Request schema for crediting a user's account."""
    user_id: str = Field(..., min_length=1, max_length=255, description="User identifier")
    amount_cents: int = Field(..., gt=0, description="Amount to credit in cents")
    reward_id: Optional[str] = Field(None, max_length=255, description="Associated reward ID")
    reward_status: Optional[RewardStatus] = Field(RewardStatus.PENDING, description="Reward lifecycle status")
    extra_data: Dict[str, Any] = Field(default_factory=dict, description="Additional context for audit trail")
    
    @validator('amount_cents')
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError("Amount must be positive")
        if v > 1_000_000_000:  # 10 million dollars max
            raise ValueError("Amount exceeds maximum allowed")
        return v


class LedgerDebitRequest(BaseModel):
    """Request schema for debiting a user's account."""
    user_id: str = Field(..., min_length=1, max_length=255, description="User identifier")
    amount_cents: int = Field(..., gt=0, description="Amount to debit in cents")
    extra_data: Dict[str, Any] = Field(default_factory=dict, description="Additional context for audit trail")
    
    @validator('amount_cents')
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError("Amount must be positive")
        return v


class LedgerReversalRequest(BaseModel):
    """Request schema for reversing a ledger entry."""
    entry_id: uuid.UUID = Field(..., description="ID of the entry to reverse")
    reason: str = Field(..., min_length=1, description="Reason for reversal")
    extra_data: Dict[str, Any] = Field(default_factory=dict, description="Additional context for audit trail")


class LedgerEntryResponse(BaseModel):
    """Response schema for a single ledger entry."""
    id: str  # UUID serialized as string for JSON
    user_id: str
    entry_type: EntryType
    amount_cents: int
    reward_id: Optional[str]
    reward_status: Optional[RewardStatus]
    idempotency_key: str
    related_entry_id: Optional[str]  # UUID serialized as string
    extra_data: Dict[str, Any]
    created_at: datetime
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            uuid.UUID: str,  # Automatically convert UUID objects to strings
        }
    
    @classmethod
    def from_orm(cls, obj):
        """Convert ORM object to response, ensuring UUIDs are strings."""
        # Helper function to recursively convert UUIDs to strings in nested dicts
        def _serialize_value(value):
            if isinstance(value, uuid.UUID):
                return str(value)
            elif isinstance(value, dict):
                return {k: _serialize_value(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [_serialize_value(item) for item in value]
            else:
                return value
        
        return cls(
            id=str(obj.id),
            user_id=obj.user_id,
            entry_type=obj.entry_type,
            amount_cents=obj.amount_cents,
            reward_id=obj.reward_id,
            reward_status=obj.reward_status,
            idempotency_key=obj.idempotency_key,
            related_entry_id=str(obj.related_entry_id) if obj.related_entry_id else None,
            extra_data=_serialize_value(obj.extra_data),  # Recursively clean UUIDs
            created_at=obj.created_at
        )


class UserBalanceResponse(BaseModel):
    """Response schema for user balance."""
    user_id: str
    balance_cents: int
    balance_dollars: float
    version: int
    updated_at: datetime
    
    @classmethod
    def from_db(cls, user_balance):
        """Create response from database model."""
        return cls(
            user_id=user_balance.user_id,
            balance_cents=user_balance.balance_cents,
            balance_dollars=user_balance.balance_cents / 100.0,
            version=user_balance.version,
            updated_at=user_balance.updated_at
        )
    
    class Config:
        from_attributes = True


class LedgerEntriesResponse(BaseModel):
    """Response schema for paginated ledger entries."""
    entries: List[LedgerEntryResponse]
    total: int
    page: int
    page_size: int


class IdempotentResponse(BaseModel):
    """Response wrapper that indicates if operation was idempotent."""
    data: LedgerEntryResponse
    is_duplicate: bool = Field(
        False, 
        description="True if this request was a duplicate and returned cached response"
    )


class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str
    detail: Optional[str] = None
    request_id: Optional[str] = None
