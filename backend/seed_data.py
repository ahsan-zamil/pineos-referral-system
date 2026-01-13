"""
Seed script to populate database with example data.

Run with: python seed_data.py
"""
import sys
import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# Add parent directory to path
sys.path.append('.')

from models import Base, LedgerEntry, UserBalance, ReferralRule, EntryType, RewardStatus
from config import settings
from rule_engine import EXAMPLE_RULES


def seed_database():
    """Seed database with example data."""
    # Create engine
    engine = create_engine(settings.DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        print("🌱 Seeding database...")
        
        # 1. Create some users with balances
        users = [
            {"user_id": "alice", "balance_cents": 50000},  # $500
            {"user_id": "bob", "balance_cents": 25000},    # $250
            {"user_id": "charlie", "balance_cents": 0},
        ]
        
        for user_data in users:
            balance = UserBalance(
                user_id=user_data["user_id"],
                balance_cents=user_data["balance_cents"],
                version=1,
                updated_at=datetime.utcnow()
            )
            session.add(balance)
            print(f"  ✓ Created balance for {user_data['user_id']}: ${user_data['balance_cents']/100:.2f}")
        
        # 2. Create some ledger entries
        ledger_entries = [
            {
                "user_id": "alice",
                "entry_type": EntryType.CREDIT,
                "amount_cents": 50000,
                "reward_id": "welcome_bonus",
                "reward_status": RewardStatus.CONFIRMED,
                "extra_data": {"source": "welcome_bonus", "description": "Welcome to PineOS!"}
            },
            {
                "user_id": "bob",
                "entry_type": EntryType.CREDIT,
                "amount_cents": 25000,
                "reward_id": "referral_bonus_001",
                "reward_status": RewardStatus.CONFIRMED,
                "extra_data": {"source": "referral", "referrer": "alice"}
            }
        ]
        
        for entry_data in ledger_entries:
            entry = LedgerEntry(
                id=uuid.uuid4(),
                user_id=entry_data["user_id"],
                entry_type=entry_data["entry_type"],
                amount_cents=entry_data["amount_cents"],
                reward_id=entry_data.get("reward_id"),
                reward_status=entry_data.get("reward_status"),
                idempotency_key=f"seed_{uuid.uuid4()}",
                extra_data=entry_data.get("extra_data", {}),
                created_at=datetime.utcnow()
            )
            session.add(entry)
            print(f"  ✓ Created {entry_data['entry_type'].value} for {entry_data['user_id']}: ${entry_data['amount_cents']/100:.2f}")
        
        # 3. Create example referral rules
        for rule_data in EXAMPLE_RULES:
            rule = ReferralRule(
                id=uuid.uuid4(),
                name=rule_data["name"],
                description=rule_data["description"],
                rule_json=rule_data["rule_json"],
                is_active=1,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            session.add(rule)
            print(f"  ✓ Created rule: {rule_data['name']}")
        
        # Commit all changes
        session.commit()
        print("\n✅ Database seeded successfully!")
        
        # Print summary
        print("\n📊 Summary:")
        print(f"  - Users: {len(users)}")
        print(f"  - Ledger Entries: {len(ledger_entries)}")
        print(f"  - Rules: {len(EXAMPLE_RULES)}")
        
    except Exception as e:
        session.rollback()
        print(f"\n❌ Error seeding database: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    seed_database()
