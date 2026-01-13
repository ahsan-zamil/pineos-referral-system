"""
FastAPI Main Application - PineOS Referral System

This application implements a production-grade financial ledger with:
- Strict idempotency guarantees
- Immutable audit trail
- ACID transaction support
- Rule-based referral engine
"""
from fastapi import FastAPI, Depends, Header, HTTPException, status, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Optional, List
import uuid

from config import settings
from database import get_db
from schemas import (
    LedgerCreditRequest, LedgerDebitRequest, LedgerReversalRequest,
    LedgerEntryResponse, UserBalanceResponse, LedgerEntriesResponse,
    IdempotentResponse, ErrorResponse
)
from ledger_service import LedgerService
from models import EntryType
from rule_api import router as rule_router


app = FastAPI(
    title="PineOS Referral System API",
    description="""
    A production-grade financial ledger system with strict idempotency guarantees.
    
    ## Key Features
    - **Immutable Ledger**: All entries are append-only
    - **Strict Idempotency**: Prevents duplicate operations via Idempotency-Key header
    - **ACID Transactions**: Balance updates are atomic
    - **Full Auditability**: Complete metadata trail for all operations
    - **Money in Cents**: Avoids floating-point errors
    
    ## Idempotency
    All mutation endpoints (POST) require an `Idempotency-Key` header.
    Use a UUID v4 for each unique request. Retrying with the same key
    returns the cached response without re-executing the operation.
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(rule_router)


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "PineOS Referral System API",
        "version": "1.0.0",
        "status": "running",
        "documentation": "/docs",
        "endpoints": {
            "ledger": {
                "credit": "POST /api/v1/ledger/credit",
                "debit": "POST /api/v1/ledger/debit",
                "reverse": "POST /api/v1/ledger/reverse",
                "entries": "GET /api/v1/ledger/entries",
                "balance": "GET /api/v1/ledger/balance/{user_id}"
            }
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {"status": "healthy", "service": "pineos-referral-system"}


# ============================================================================
# LEDGER ENDPOINTS
# ============================================================================

@app.post(
    f"{settings.API_V1_PREFIX}/ledger/credit",
    response_model=IdempotentResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Credit successfully applied"},
        200: {"description": "Duplicate request - returning cached response"},
        409: {"description": "Idempotency key conflict"},
        422: {"description": "Validation error"}
    },
    summary="Credit a user's account",
    description="""
    Credit a user's account with strict idempotency guarantees.
    
    **Idempotency**: Requires `Idempotency-Key` header (UUID recommended).
    Duplicate requests return cached response with HTTP 200 instead of 201.
    
    **ACID**: Balance updates are atomic with ledger entry creation.
    
    **Auditability**: Full metadata trail stored in ledger_entries table.
    """
)
async def credit_account(
    request: LedgerCreditRequest,
    idempotency_key: str = Header(..., description="Unique key to prevent duplicate operations"),
    db: Session = Depends(get_db)
):
    """Credit a user's account."""
    service = LedgerService(db)
    
    try:
        entry, is_duplicate = service.credit(request, idempotency_key)
        
        response = IdempotentResponse(
            data=LedgerEntryResponse.from_orm(entry),
            is_duplicate=is_duplicate
        )
        
        # Always use JSONResponse with explicit serialization
        if is_duplicate:
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content=response.model_dump(mode='json')
            )
        
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content=response.model_dump(mode='json')
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.post(
    f"{settings.API_V1_PREFIX}/ledger/debit",
    response_model=IdempotentResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Debit successfully applied"},
        200: {"description": "Duplicate request - returning cached response"},
        400: {"description": "Insufficient balance"},
        409: {"description": "Idempotency key conflict"}
    },
    summary="Debit a user's account",
    description="""
    Debit a user's account with balance validation and idempotency.
    
    **Balance Check**: Validates sufficient balance before debiting.
    
    **Idempotency**: Requires `Idempotency-Key` header.
    """
)
async def debit_account(
    request: LedgerDebitRequest,
    idempotency_key: str = Header(..., description="Unique key to prevent duplicate operations"),
    db: Session = Depends(get_db)
):
    """Debit a user's account."""
    service = LedgerService(db)
    
    try:
        entry, is_duplicate = service.debit(request, idempotency_key)
        
        response = IdempotentResponse(
            data=LedgerEntryResponse.from_orm(entry),
            is_duplicate=is_duplicate
        )
        
        # Always use JSONResponse with explicit serialization
        if is_duplicate:
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content=response.model_dump(mode='json')
            )
        
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content=response.model_dump(mode='json')
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.post(
    f"{settings.API_V1_PREFIX}/ledger/reverse",
    response_model=IdempotentResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Reversal successfully created"},
        200: {"description": "Duplicate request - returning cached response"},
        404: {"description": "Original entry not found"},
        409: {"description": "Entry already reversed or idempotency conflict"}
    },
    summary="Reverse a ledger entry",
    description="""
    Reverse a previous ledger entry by creating an offsetting entry.
    
    **Immutability**: Original entry remains unchanged.
    
    **Linking**: Reversal entry links to original via related_entry_id.
    
    **Balance Adjustment**: Automatically adjusts balance in opposite direction.
    """
)
async def reverse_entry(
    request: LedgerReversalRequest,
    idempotency_key: str = Header(..., description="Unique key to prevent duplicate operations"),
    db: Session = Depends(get_db)
):
    """Reverse a ledger entry."""
    service = LedgerService(db)
    
    try:
        entry, is_duplicate = service.reverse(request, idempotency_key)
        
        response = IdempotentResponse(
            data=LedgerEntryResponse.from_orm(entry),
            is_duplicate=is_duplicate
        )
        
        # Always use JSONResponse with explicit serialization
        if is_duplicate:
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content=response.model_dump(mode='json')
            )
        
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content=response.model_dump(mode='json')
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.get(
    f"{settings.API_V1_PREFIX}/ledger/entries",
    response_model=LedgerEntriesResponse,
    summary="Get ledger entries",
    description="Fetch ledger entries with optional user filter and pagination."
)
async def get_entries(
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum entries to return"),
    offset: int = Query(0, ge=0, description="Number of entries to skip"),
    db: Session = Depends(get_db)
):
    """Get ledger entries with optional filtering."""
    service = LedgerService(db)
    
    entries = service.get_entries(user_id=user_id, limit=limit, offset=offset)
    
    # Get total count
    from models import LedgerEntry
    query = db.query(LedgerEntry)
    if user_id:
        query = query.filter(LedgerEntry.user_id == user_id)
    total = query.count()
    
    return LedgerEntriesResponse(
        entries=[LedgerEntryResponse.from_orm(e) for e in entries],
        total=total,
        page=offset // limit + 1 if limit > 0 else 1,
        page_size=limit
    )


@app.get(
    f"{settings.API_V1_PREFIX}/ledger/balance/{{user_id}}",
    response_model=UserBalanceResponse,
    summary="Get user balance",
    description="Fetch current balance for a user."
)
async def get_balance(
    user_id: str,
    db: Session = Depends(get_db)
):
    """Get user's current balance."""
    service = LedgerService(db)
    balance = service.get_balance(user_id)
    
    return UserBalanceResponse.from_db(balance)


# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Custom error response format."""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=exc.detail,
            detail=getattr(exc, "detail", None)
        ).model_dump(mode='json')
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=True
    )
