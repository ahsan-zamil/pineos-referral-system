"""
Rule-based referral engine for evaluating events and triggering rewards.

Rule Format (JSON):
{
    "conditions": [
        {"field": "referrer.is_paid_user", "operator": "==", "value": true},
        {"field": "referred.subscription_status", "operator": "==", "value": "active"}
    ],
    "actions": [
        {"type": "credit", "user": "referrer", "amount_cents": 50000, "reward_id": "referral_bonus"}
    ],
    "logic": "AND"  // or "OR"
}

Example Rules:
1. "If referrer is paid user AND referred user subscribes → reward ₹500"
2. "If user makes 5 successful referrals → reward ₹1000 bonus"
3. "If referred user's first purchase > ₹1000 → reward ₹200"
"""
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from models import ReferralRule, EntryType, RewardStatus
from ledger_service import LedgerService
from schemas import LedgerCreditRequest
import uuid
import json
from datetime import datetime


class RuleEngine:
    """Evaluates events against defined rules and triggers actions."""
    
    def __init__(self, db: Session):
        self.db = db
        self.ledger_service = LedgerService(db)
    
    def _evaluate_condition(self, condition: Dict, event_data: Dict) -> bool:
        """
        Evaluate a single condition against event data.
        
        Args:
            condition: {"field": "user.is_paid", "operator": "==", "value": true}
            event_data: Actual event data
        
        Returns:
            True if condition matches, False otherwise
        """
        field_path = condition.get("field", "")
        operator = condition.get("operator", "==")
        expected_value = condition.get("value")
        
        # Extract value from nested field path (e.g., "user.is_paid")
        actual_value = event_data
        for key in field_path.split("."):
            if isinstance(actual_value, dict):
                actual_value = actual_value.get(key)
            else:
                return False
        
        # Evaluate operator
        if operator == "==":
            return actual_value == expected_value
        elif operator == "!=":
            return actual_value != expected_value
        elif operator == ">":
            return actual_value > expected_value
        elif operator == "<":
            return actual_value < expected_value
        elif operator == ">=":
            return actual_value >= expected_value
        elif operator == "<=":
            return actual_value <= expected_value
        elif operator == "in":
            return actual_value in expected_value
        elif operator == "not_in":
            return actual_value not in expected_value
        elif operator == "contains":
            return expected_value in actual_value
        else:
            return False
    
    def _evaluate_conditions(
        self, 
        conditions: List[Dict], 
        event_data: Dict,
        logic: str = "AND"
    ) -> bool:
        """
        Evaluate all conditions with specified logic.
        
        Args:
            conditions: List of condition dictionaries
            event_data: Event data to evaluate against
            logic: "AND" or "OR"
        
        Returns:
            True if conditions match, False otherwise
        """
        if not conditions:
            return True
        
        results = [self._evaluate_condition(c, event_data) for c in conditions]
        
        if logic == "AND":
            return all(results)
        elif logic == "OR":
            return any(results)
        else:
            return all(results)  # Default to AND
    
    def _execute_action(self, action: Dict, event_data: Dict) -> Dict[str, Any]:
        """
        Execute a single action.
        
        Args:
            action: Action definition from rule
            event_data: Event context for user IDs, etc.
        
        Returns:
            Result of action execution
        """
        action_type = action.get("type")
        
        if action_type == "credit":
            # Extract user ID from event data based on action spec
            user_field = action.get("user", "user_id")
            user_id = event_data.get(user_field)
            
            if not user_id:
                return {
                    "success": False,
                    "error": f"User field '{user_field}' not found in event data"
                }
            
            # Create credit request
            amount_cents = action.get("amount_cents", 0)
            reward_id = action.get("reward_id", str(uuid.uuid4()))
            
            credit_request = LedgerCreditRequest(
                user_id=str(user_id),
                amount_cents=amount_cents,
                reward_id=reward_id,
                reward_status=RewardStatus.CONFIRMED,
                extra_data={
                    "source": "rule_engine",
                    "action": action,
                    "event_data": event_data,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            
            # Generate idempotency key from event + rule + user
            idempotency_data = f"{reward_id}:{user_id}:{event_data.get('event_id', '')}"
            idempotency_key = str(uuid.uuid5(uuid.NAMESPACE_DNS, idempotency_data))
            
            try:
                entry, is_duplicate = self.ledger_service.credit(
                    credit_request, 
                    idempotency_key
                )
                
                return {
                    "success": True,
                    "action_type": "credit",
                    "entry_id": str(entry.id),
                    "user_id": user_id,
                    "amount_cents": amount_cents,
                    "is_duplicate": is_duplicate
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": str(e)
                }
        
        elif action_type == "debit":
            # Similar to credit but debit
            # Implement if needed
            return {"success": False, "error": "Debit action not implemented"}
        
        else:
            return {
                "success": False,
                "error": f"Unknown action type: {action_type}"
            }
    
    def evaluate_event(self, event_data: Dict[str, Any], rule_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Evaluate an event against rules and execute matching actions.
        
        Args:
            event_data: Event data to evaluate
            rule_id: Optional specific rule ID to evaluate, otherwise all active rules
        
        Returns:
            Dictionary with evaluation results
        """
        # Fetch rules
        query = self.db.query(ReferralRule).filter(ReferralRule.is_active == 1)
        
        if rule_id:
            query = query.filter(ReferralRule.id == rule_id)
        
        rules = query.all()
        
        results = []
        
        for rule in rules:
            rule_json = rule.rule_json
            
            # Evaluate conditions
            conditions = rule_json.get("conditions", [])
            logic = rule_json.get("logic", "AND")
            
            conditions_met = self._evaluate_conditions(conditions, event_data, logic)
            
            if conditions_met:
                # Execute actions
                actions = rule_json.get("actions", [])
                action_results = []
                
                for action in actions:
                    result = self._execute_action(action, event_data)
                    action_results.append(result)
                
                results.append({
                    "rule_id": str(rule.id),
                    "rule_name": rule.name,
                    "conditions_met": True,
                    "actions_executed": action_results
                })
            else:
                results.append({
                    "rule_id": str(rule.id),
                    "rule_name": rule.name,
                    "conditions_met": False,
                    "actions_executed": []
                })
        
        return {
            "event_data": event_data,
            "rules_evaluated": len(results),
            "rules_triggered": sum(1 for r in results if r["conditions_met"]),
            "results": results
        }
    
    def create_rule(
        self, 
        name: str, 
        rule_json: Dict[str, Any],
        description: Optional[str] = None
    ) -> ReferralRule:
        """Create a new referral rule."""
        rule = ReferralRule(
            id=uuid.uuid4(),
            name=name,
            description=description,
            rule_json=rule_json,
            is_active=1,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        self.db.add(rule)
        self.db.commit()
        self.db.refresh(rule)
        
        return rule
    
    def get_rules(self, active_only: bool = True) -> List[ReferralRule]:
        """Fetch all rules."""
        query = self.db.query(ReferralRule)
        
        if active_only:
            query = query.filter(ReferralRule.is_active == 1)
        
        return query.all()
    
    def get_rule(self, rule_id: str) -> Optional[ReferralRule]:
        """Fetch a specific rule by ID."""
        return self.db.query(ReferralRule).filter(ReferralRule.id == rule_id).first()


# Example rules for testing
EXAMPLE_RULES = [
    {
        "name": "Paid User Referral Bonus",
        "description": "Reward ₹500 when a paid user refers someone who subscribes",
        "rule_json": {
            "conditions": [
                {"field": "referrer.is_paid_user", "operator": "==", "value": True},
                {"field": "referred.subscription_status", "operator": "==", "value": "active"}
            ],
            "actions": [
                {
                    "type": "credit",
                    "user": "referrer_id",
                    "amount_cents": 50000,
                    "reward_id": "referral_bonus"
                }
            ],
            "logic": "AND"
        }
    },
    {
        "name": "First Purchase Bonus",
        "description": "Reward ₹200 when referred user makes first purchase > ₹1000",
        "rule_json": {
            "conditions": [
                {"field": "purchase.is_first", "operator": "==", "value": True},
                {"field": "purchase.amount_cents", "operator": ">", "value": 100000}
            ],
            "actions": [
                {
                    "type": "credit",
                    "user": "referrer_id",
                    "amount_cents": 20000,
                    "reward_id": "first_purchase_bonus"
                }
            ],
            "logic": "AND"
        }
    }
]
