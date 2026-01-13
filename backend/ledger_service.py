"""
Financial Ledger Service with strict idempotency guarantees.

Design Principles:
1. Immutability: All ledger entries are append-only
2. Idempotency: Using idempotency keys to prevent duplicate operations
3. ACID Transactions: All balance updates happen atomically
4. Auditability: Full metadata tracking for all operations
5. Double-Entry Accounting: Credits must balance with debits

Idempotency Strategy:
- Client provides Idempotency-Key header (UUID recommended)
- Server hashes request body + idempotency key
- If duplicate detected: return cached response (201 -> 200)
- Prevents: double credits, race conditions, network retry issues
"""
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from models import (
    LedgerEntry, UserBalance, EntryType, RewardStatus, IdempotencyRecord
)
from schemas import (
    LedgerCreditRequest, LedgerDebitRequest, LedgerReversalRequest,
    LedgerEntryResponse, IdempotentResponse
)
import hashlib
import json
import uuid
from datetime import datetime
from typing import Optional, List, Tuple
from fastapi import HTTPException, status


class LedgerService:
    """Service for managing financial ledger operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def _compute_request_hash(self, request_data: dict) -> str:
        """Compute SHA-256 hash of request data for idempotency check."""
        request_json = json.dumps(request_data, sort_keys=True)
        return hashlib.sha256(request_json.encode()).hexdigest()
    
    def _check_idempotency(
        self, 
        idempotency_key: str, 
        request_data: dict
    ) -> Optional[LedgerEntry]:
        """
        Check if request is duplicate based on idempotency key.
        
        Returns:
            - Existing LedgerEntry if duplicate found
            - None if this is a new request
        
        Raises:
            - HTTPException if idempotency key exists but request differs
        """
        existing_entry = (
            self.db.query(LedgerEntry)
            .filter(LedgerEntry.idempotency_key == idempotency_key)
            .first()
        )
        
        if existing_entry:
            # Found existing entry - verify request is identical
            request_hash = self._compute_request_hash(request_data)
            stored_hash = existing_entry.extra_data.get("request_hash", "")
            
            if request_hash != stored_hash:
                # Same idempotency key, different request = error
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Idempotency key already used with different request"
                )
            
            return existing_entry
        
        return None
    
    def _get_or_create_balance(self, user_id: str) -> UserBalance:
        """Get user balance, creating if doesn't exist."""
        balance = (
            self.db.query(UserBalance)
            .filter(UserBalance.user_id == user_id)
            .with_for_update()  # Lock row for update
            .first()
        )
        
        if not balance:
            balance = UserBalance(
                user_id=user_id,
                balance_cents=0,
                version=1
            )
            self.db.add(balance)
            self.db.flush()  # Get ID without committing
        
        return balance
    
    def credit(
        self, 
        request: LedgerCreditRequest, 
        idempotency_key: str
    ) -> Tuple[LedgerEntry, bool]:
        """
        Credit a user's account with strict idempotency.
        
        Args:
            request: Credit request details
            idempotency_key: Unique key to prevent duplicate operations
        
        Returns:
            Tuple of (LedgerEntry, is_duplicate)
        
        Raises:
            HTTPException on validation or idempotency errors
        """
        # Prepare request data for idempotency check
        request_data = request.model_dump()
        request_hash = self._compute_request_hash(request_data)
        
        # Check for duplicate request
        existing_entry = self._check_idempotency(idempotency_key, request_data)
        if existing_entry:
            return existing_entry, True  # Duplicate - return cached
        
        try:
            # Get or create user balance (with row lock)
            user_balance = self._get_or_create_balance(request.user_id)
            
            # Add extra_data for audit trail
            entry_extra_data = {
                **request.extra_data,
                "request_hash": request_hash,
                "operation": "credit",
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Create immutable ledger entry
            ledger_entry = LedgerEntry(
                id=uuid.uuid4(),
                user_id=request.user_id,
                entry_type=EntryType.CREDIT,
                amount_cents=request.amount_cents,
                reward_id=request.reward_id,
                reward_status=request.reward_status or RewardStatus.PENDING,
                idempotency_key=idempotency_key,
                extra_data=entry_extra_data,
                created_at=datetime.utcnow()
            )
            
            # Update balance atomically
            user_balance.balance_cents += request.amount_cents
            user_balance.version += 1
            user_balance.updated_at = datetime.utcnow()
            
            # Add to session
            self.db.add(ledger_entry)
            
            # Commit transaction (ACID guarantee)
            self.db.commit()
            self.db.refresh(ledger_entry)
            
            return ledger_entry, False
            
        except IntegrityError as e:
            self.db.rollback()
            # Handle race condition on idempotency key
            if "idempotency_key" in str(e):
                # Another request won the race - fetch and return
                entry = (
                    self.db.query(LedgerEntry)
                    .filter(LedgerEntry.idempotency_key == idempotency_key)
                    .first()
                )
                if entry:
                    return entry, True
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database error: {str(e)}"
            )
        except Exception as e:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Unexpected error: {str(e)}"
            )
    
    def debit(
        self, 
        request: LedgerDebitRequest, 
        idempotency_key: str
    ) -> Tuple[LedgerEntry, bool]:
        """
        Debit a user's account with strict idempotency.
        
        Similar to credit but validates sufficient balance.
        """
        request_data = request.model_dump()
        request_hash = self._compute_request_hash(request_data)
        
        # Check for duplicate
        existing_entry = self._check_idempotency(idempotency_key, request_data)
        if existing_entry:
            return existing_entry, True
        
        try:
            # Get balance with lock
            user_balance = self._get_or_create_balance(request.user_id)
            
            # Validate sufficient balance
            if user_balance.balance_cents < request.amount_cents:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Insufficient balance. Available: {user_balance.balance_cents} cents, Required: {request.amount_cents} cents"
                )
            
            # Create ledger entry
            entry_extra_data = {
                **request.extra_data,
                "request_hash": request_hash,
                "operation": "debit",
                "timestamp": datetime.utcnow().isoformat()
            }
            
            ledger_entry = LedgerEntry(
                id=uuid.uuid4(),
                user_id=request.user_id,
                entry_type=EntryType.DEBIT,
                amount_cents=request.amount_cents,
                idempotency_key=idempotency_key,
                extra_data=entry_extra_data,
                created_at=datetime.utcnow()
            )
            
            # Update balance
            user_balance.balance_cents -= request.amount_cents
            user_balance.version += 1
            user_balance.updated_at = datetime.utcnow()
            
            self.db.add(ledger_entry)
            self.db.commit()
            self.db.refresh(ledger_entry)
            
            return ledger_entry, False
            
        except IntegrityError as e:
            self.db.rollback()
            if "idempotency_key" in str(e):
                entry = (
                    self.db.query(LedgerEntry)
                    .filter(LedgerEntry.idempotency_key == idempotency_key)
                    .first()
                )
                if entry:
                    return entry, True
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database error: {str(e)}"
            )
        except HTTPException:
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Unexpected error: {str(e)}"
            )
    
    def reverse(
        self, 
        request: LedgerReversalRequest, 
        idempotency_key: str
    ) -> Tuple[LedgerEntry, bool]:
        """
        Reverse a previous ledger entry by creating an offsetting entry.
        
        Reversal strategy:
        - Creates new ledger entry with type=REVERSAL
        - Links to original entry via related_entry_id
        - Adjusts balance in opposite direction
        - Original entry remains immutable
        """
        request_data = request.model_dump()
        request_hash = self._compute_request_hash(request_data)
        
        # Check for duplicate
        existing_entry = self._check_idempotency(idempotency_key, request_data)
        if existing_entry:
            return existing_entry, True
        
        try:
            # Fetch original entry
            original_entry = (
                self.db.query(LedgerEntry)
                .filter(LedgerEntry.id == request.entry_id)
                .first()
            )
            
            if not original_entry:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Ledger entry {request.entry_id} not found"
                )
            
            # Check if already reversed
            existing_reversal = (
                self.db.query(LedgerEntry)
                .filter(
                    LedgerEntry.entry_type == EntryType.REVERSAL,
                    LedgerEntry.related_entry_id == request.entry_id
                )
                .first()
            )
            
            if existing_reversal:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Entry {request.entry_id} already reversed"
                )
            
            # Get user balance with lock
            user_balance = self._get_or_create_balance(original_entry.user_id)
            
            # Create reversal entry
            entry_extra_data = {
                **request.extra_data,
                "request_hash": request_hash,
                "operation": "reversal",
                "original_entry_id": str(original_entry.id),
                "original_entry_type": original_entry.entry_type.value,
                "reason": request.reason,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            reversal_entry = LedgerEntry(
                id=uuid.uuid4(),
                user_id=original_entry.user_id,
                entry_type=EntryType.REVERSAL,
                amount_cents=original_entry.amount_cents,
                reward_id=original_entry.reward_id,
                reward_status=RewardStatus.REVERSED if original_entry.reward_status else None,
                idempotency_key=idempotency_key,
                related_entry_id=original_entry.id,
                extra_data=entry_extra_data,
                created_at=datetime.utcnow()
            )
            
            # Adjust balance (opposite of original)
            if original_entry.entry_type == EntryType.CREDIT:
                # Reversing a credit = debit
                if user_balance.balance_cents < original_entry.amount_cents:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Insufficient balance to reverse credit"
                    )
                user_balance.balance_cents -= original_entry.amount_cents
            elif original_entry.entry_type == EntryType.DEBIT:
                # Reversing a debit = credit
                user_balance.balance_cents += original_entry.amount_cents
            
            user_balance.version += 1
            user_balance.updated_at = datetime.utcnow()
            
            self.db.add(reversal_entry)
            self.db.commit()
            self.db.refresh(reversal_entry)
            
            return reversal_entry, False
            
        except IntegrityError as e:
            self.db.rollback()
            if "idempotency_key" in str(e):
                entry = (
                    self.db.query(LedgerEntry)
                    .filter(LedgerEntry.idempotency_key == idempotency_key)
                    .first()
                )
                if entry:
                    return entry, True
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database error: {str(e)}"
            )
        except HTTPException:
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Unexpected error: {str(e)}"
            )
    
    def get_entries(
        self, 
        user_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[LedgerEntry]:
        """Fetch ledger entries with optional user filter."""
        query = self.db.query(LedgerEntry)
        
        if user_id:
            query = query.filter(LedgerEntry.user_id == user_id)
        
        query = query.order_by(LedgerEntry.created_at.desc())
        query = query.offset(offset).limit(limit)
        
        return query.all()
    
    def get_balance(self, user_id: str) -> UserBalance:
        """Get user's current balance."""
        balance = (
            self.db.query(UserBalance)
            .filter(UserBalance.user_id == user_id)
            .first()
        )
        
        if not balance:
            # Create zero balance if user doesn't exist
            balance = UserBalance(
                user_id=user_id,
                balance_cents=0,
                version=1,
                updated_at=datetime.utcnow()
            )
        
        return balance
