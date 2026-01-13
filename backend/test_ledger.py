"""
Comprehensive tests for the financial ledger system.

Tests cover:
1. Idempotency: Duplicate requests don't double-credit
2. Balance Correctness: Credits/debits update balances correctly
3. Reversal Behavior: Reversals create offsetting entries
4. ACID Transactions: Operations are atomic
5. Error Handling: Proper validation and error responses
"""
import pytest
from fastapi import status
import uuid


class TestIdempotency:
    """Test suite for idempotency guarantees."""
    
    def test_duplicate_credit_returns_same_response(self, client, idempotency_key):
        """
        CRITICAL TEST: Duplicate credit requests must not double-credit.
        
        This is the core idempotency test required by the challenge.
        """
        credit_data = {
            "user_id": "user_123",
            "amount_cents": 10000,  # $100.00
            "reward_id": "reward_xyz",
            "extra_data": {"source": "referral_bonus"}
        }
        
        # First request - should create entry
        response1 = client.post(
            "/api/v1/ledger/credit",
            json=credit_data,
            headers={"Idempotency-Key": idempotency_key}
        )
        
        assert response1.status_code == status.HTTP_201_CREATED
        data1 = response1.json()
        assert data1["is_duplicate"] is False
        entry_id_1 = data1["data"]["id"]
        
        # Second request with SAME idempotency key - should return cached
        response2 = client.post(
            "/api/v1/ledger/credit",
            json=credit_data,
            headers={"Idempotency-Key": idempotency_key}
        )
        
        assert response2.status_code == status.HTTP_200_OK  # 200 for duplicate
        data2 = response2.json()
        assert data2["is_duplicate"] is True
        entry_id_2 = data2["data"]["id"]
        
        # Same entry returned
        assert entry_id_1 == entry_id_2
        
        # Verify balance only credited once
        balance_response = client.get("/api/v1/ledger/balance/user_123")
        assert balance_response.status_code == status.HTTP_200_OK
        balance = balance_response.json()
        assert balance["balance_cents"] == 10000  # Only $100, not $200
    
    def test_different_idempotency_keys_create_different_entries(
        self, client, idempotency_key, second_idempotency_key
    ):
        """Different idempotency keys should create separate entries."""
        credit_data = {
            "user_id": "user_456",
            "amount_cents": 5000
        }
        
        # First request
        response1 = client.post(
            "/api/v1/ledger/credit",
            json=credit_data,
            headers={"Idempotency-Key": idempotency_key}
        )
        
        # Second request with different key
        response2 = client.post(
            "/api/v1/ledger/credit",
            json=credit_data,
            headers={"Idempotency-Key": second_idempotency_key}
        )
        
        assert response1.status_code == status.HTTP_201_CREATED
        assert response2.status_code == status.HTTP_201_CREATED
        
        # Different entry IDs
        assert response1.json()["data"]["id"] != response2.json()["data"]["id"]
        
        # Balance credited twice
        balance_response = client.get("/api/v1/ledger/balance/user_456")
        balance = balance_response.json()
        assert balance["balance_cents"] == 10000  # $50 + $50
    
    def test_same_key_different_request_returns_conflict(self, client, idempotency_key):
        """
        Using same idempotency key with different request data should error.
        
        This prevents accidental reuse of idempotency keys.
        """
        # First request
        client.post(
            "/api/v1/ledger/credit",
            json={"user_id": "user_789", "amount_cents": 1000},
            headers={"Idempotency-Key": idempotency_key}
        )
        
        # Second request with DIFFERENT data but SAME key
        response = client.post(
            "/api/v1/ledger/credit",
            json={"user_id": "user_789", "amount_cents": 2000},  # Different amount
            headers={"Idempotency-Key": idempotency_key}
        )
        
        assert response.status_code == status.HTTP_409_CONFLICT


class TestBalanceCorrectness:
    """Test that balances are correctly updated."""
    
    def test_credit_increases_balance(self, client, idempotency_key):
        """Crediting should increase user balance."""
        response = client.post(
            "/api/v1/ledger/credit",
            json={"user_id": "user_balance_1", "amount_cents": 15000},
            headers={"Idempotency-Key": idempotency_key}
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        
        balance_response = client.get("/api/v1/ledger/balance/user_balance_1")
        assert balance_response.json()["balance_cents"] == 15000
    
    def test_debit_decreases_balance(self, client, idempotency_key, second_idempotency_key):
        """Debiting should decrease user balance."""
        # First credit some money
        client.post(
            "/api/v1/ledger/credit",
            json={"user_id": "user_balance_2", "amount_cents": 20000},
            headers={"Idempotency-Key": idempotency_key}
        )
        
        # Then debit
        response = client.post(
            "/api/v1/ledger/debit",
            json={"user_id": "user_balance_2", "amount_cents": 7000},
            headers={"Idempotency-Key": second_idempotency_key}
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        
        balance_response = client.get("/api/v1/ledger/balance/user_balance_2")
        assert balance_response.json()["balance_cents"] == 13000  # 20000 - 7000
    
    def test_debit_insufficient_balance_fails(self, client, idempotency_key):
        """Debiting more than balance should fail."""
        # Credit $50
        client.post(
            "/api/v1/ledger/credit",
            json={"user_id": "user_balance_3", "amount_cents": 5000},
            headers={"Idempotency-Key": str(uuid.uuid4())}
        )
        
        # Try to debit $100
        response = client.post(
            "/api/v1/ledger/debit",
            json={"user_id": "user_balance_3", "amount_cents": 10000},
            headers={"Idempotency-Key": idempotency_key}
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Insufficient balance" in response.json()["error"]
    
    def test_multiple_operations_balance_consistency(self, client):
        """Test balance consistency across multiple operations."""
        user_id = "user_balance_4"
        
        # Credit $100
        client.post(
            "/api/v1/ledger/credit",
            json={"user_id": user_id, "amount_cents": 10000},
            headers={"Idempotency-Key": str(uuid.uuid4())}
        )
        
        # Credit $50
        client.post(
            "/api/v1/ledger/credit",
            json={"user_id": user_id, "amount_cents": 5000},
            headers={"Idempotency-Key": str(uuid.uuid4())}
        )
        
        # Debit $30
        client.post(
            "/api/v1/ledger/debit",
            json={"user_id": user_id, "amount_cents": 3000},
            headers={"Idempotency-Key": str(uuid.uuid4())}
        )
        
        balance_response = client.get(f"/api/v1/ledger/balance/{user_id}")
        assert balance_response.json()["balance_cents"] == 12000  # 100 + 50 - 30


class TestReversalBehavior:
    """Test reversal functionality."""
    
    def test_reverse_credit_creates_offsetting_entry(self, client, idempotency_key, second_idempotency_key):
        """Reversing a credit should create a reversal entry and adjust balance."""
        user_id = "user_reversal_1"
        
        # Credit $100
        credit_response = client.post(
            "/api/v1/ledger/credit",
            json={"user_id": user_id, "amount_cents": 10000},
            headers={"Idempotency-Key": idempotency_key}
        )
        
        entry_id = credit_response.json()["data"]["id"]
        
        # Reverse the credit
        reversal_response = client.post(
            "/api/v1/ledger/reverse",
            json={
                "entry_id": entry_id,
                "reason": "User not eligible",
                "extra_data": {"admin_id": "admin_123"}
            },
            headers={"Idempotency-Key": second_idempotency_key}
        )
        
        assert reversal_response.status_code == status.HTTP_201_CREATED
        reversal_data = reversal_response.json()["data"]
        
        # Verify reversal entry
        assert reversal_data["entry_type"] == "reversal"
        assert reversal_data["related_entry_id"] == entry_id
        assert reversal_data["amount_cents"] == 10000
        assert "reason" in reversal_data["extra_data"]
        
        # Verify balance is back to zero
        balance_response = client.get(f"/api/v1/ledger/balance/{user_id}")
        assert balance_response.json()["balance_cents"] == 0
    
    def test_cannot_reverse_same_entry_twice(self, client):
        """Attempting to reverse same entry twice should fail."""
        user_id = "user_reversal_2"
        
        # Credit
        credit_response = client.post(
            "/api/v1/ledger/credit",
            json={"user_id": user_id, "amount_cents": 5000},
            headers={"Idempotency-Key": str(uuid.uuid4())}
        )
        
        entry_id = credit_response.json()["data"]["id"]
        
        # First reversal
        client.post(
            "/api/v1/ledger/reverse",
            json={"entry_id": entry_id, "reason": "First reversal"},
            headers={"Idempotency-Key": str(uuid.uuid4())}
        )
        
        # Second reversal attempt
        response = client.post(
            "/api/v1/ledger/reverse",
            json={"entry_id": entry_id, "reason": "Second reversal"},
            headers={"Idempotency-Key": str(uuid.uuid4())}
        )
        
        assert response.status_code == status.HTTP_409_CONFLICT
        assert "already reversed" in response.json()["error"]
    
    def test_reverse_nonexistent_entry_fails(self, client, idempotency_key):
        """Reversing non-existent entry should fail."""
        fake_entry_id = str(uuid.uuid4())
        
        response = client.post(
            "/api/v1/ledger/reverse",
            json={"entry_id": fake_entry_id, "reason": "Test"},
            headers={"Idempotency-Key": idempotency_key}
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestLedgerEntries:
    """Test ledger entries retrieval."""
    
    def test_get_all_entries(self, client):
        """Test fetching all ledger entries."""
        # Create some entries
        for i in range(3):
            client.post(
                "/api/v1/ledger/credit",
                json={"user_id": f"user_{i}", "amount_cents": 1000 * (i + 1)},
                headers={"Idempotency-Key": str(uuid.uuid4())}
            )
        
        response = client.get("/api/v1/ledger/entries")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert data["total"] >= 3
        assert len(data["entries"]) >= 3
    
    def test_get_entries_filtered_by_user(self, client):
        """Test filtering entries by user ID."""
        target_user = "user_filter_test"
        
        # Create entries for different users
        client.post(
            "/api/v1/ledger/credit",
            json={"user_id": target_user, "amount_cents": 1000},
            headers={"Idempotency-Key": str(uuid.uuid4())}
        )
        
        client.post(
            "/api/v1/ledger/credit",
            json={"user_id": "other_user", "amount_cents": 2000},
            headers={"Idempotency-Key": str(uuid.uuid4())}
        )
        
        # Filter by target user
        response = client.get(f"/api/v1/ledger/entries?user_id={target_user}")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert all(entry["user_id"] == target_user for entry in data["entries"])


class TestAPIBasics:
    """Test basic API functionality."""
    
    def test_health_check(self, client):
        """Health endpoint should return healthy status."""
        response = client.get("/health")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["status"] == "healthy"
    
    def test_root_endpoint(self, client):
        """Root endpoint should return API info."""
        response = client.get("/")
        assert response.status_code == status.HTTP_200_OK
        assert "version" in response.json()
    
    def test_missing_idempotency_key_fails(self, client):
        """Requests without idempotency key should fail."""
        response = client.post(
            "/api/v1/ledger/credit",
            json={"user_id": "user_x", "amount_cents": 1000}
            # No Idempotency-Key header
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# Run with: pytest -v test_ledger.py
