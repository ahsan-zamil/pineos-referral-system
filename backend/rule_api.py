"""
API endpoints for rule engine management and evaluation.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
import uuid

from database import get_db
from rule_engine import RuleEngine, EXAMPLE_RULES
from ai_service import AIService


router = APIRouter(prefix="/api/v1/rules", tags=["rules"])


# ============================================================================
# SCHEMAS
# ============================================================================

class RuleCondition(BaseModel):
    """Schema for a rule condition."""
    field: str = Field(..., description="Field path to evaluate (e.g., 'user.is_paid')")
    operator: str = Field(..., description="Comparison operator: ==, !=, >, <, >=, <=, in, contains")
    value: Any = Field(..., description="Expected value")


class RuleAction(BaseModel):
    """Schema for a rule action."""
    type: str = Field(..., description="Action type: credit, debit, etc.")
    user: str = Field("user_id", description="Field name for user ID in event data")
    amount_cents: int = Field(..., gt=0, description="Amount in cents")
    reward_id: str = Field(..., description="Reward identifier")


class RuleJSON(BaseModel):
    """Schema for rule definition."""
    conditions: List[RuleCondition]
    actions: List[RuleAction]
    logic: str = Field("AND", description="Logic to combine conditions: AND or OR")


class CreateRuleRequest(BaseModel):
    """Request to create a new rule."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    rule_json: RuleJSON


class RuleResponse(BaseModel):
    """Response schema for a rule."""
    id: str
    name: str
    description: Optional[str]
    rule_json: Dict[str, Any]
    is_active: int
    created_at: str
    updated_at: str


class EvaluateEventRequest(BaseModel):
    """Request to evaluate an event against rules."""
    event_data: Dict[str, Any] = Field(..., description="Event data to evaluate")
    rule_id: Optional[str] = Field(None, description="Optional: Evaluate against specific rule")


class EvaluationResult(BaseModel):
    """Result of event evaluation."""
    event_data: Dict[str, Any]
    rules_evaluated: int
    rules_triggered: int
    results: List[Dict[str, Any]]


class NaturalLanguageRequest(BaseModel):
    """Request to convert natural language to rule JSON."""
    description: str = Field(
        ..., 
        min_length=10,
        description="Natural language description of the rule"
    )
    rule_name: Optional[str] = Field(
        None,
        description="Optional custom name for the rule"
    )


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/", response_model=RuleResponse, status_code=status.HTTP_201_CREATED)
async def create_rule(
    request: CreateRuleRequest,
    db: Session = Depends(get_db)
):
    """
    Create a new referral rule.
    
    Rules consist of:
    - **Conditions**: Field comparisons that must be met
    - **Actions**: Operations to execute when conditions match
    - **Logic**: How to combine conditions (AND/OR)
    """
    engine = RuleEngine(db)
    
    rule = engine.create_rule(
        name=request.name,
        description=request.description,
        rule_json=request.rule_json.model_dump()
    )
    
    return RuleResponse(
        id=str(rule.id),
        name=rule.name,
        description=rule.description,
        rule_json=rule.rule_json,
        is_active=rule.is_active,
        created_at=rule.created_at.isoformat(),
        updated_at=rule.updated_at.isoformat()
    )


@router.get("/", response_model=List[RuleResponse])
async def get_rules(
    active_only: bool = True,
    db: Session = Depends(get_db)
):
    """Fetch all rules."""
    engine = RuleEngine(db)
    rules = engine.get_rules(active_only=active_only)
    
    return [
        RuleResponse(
            id=str(rule.id),
            name=rule.name,
            description=rule.description,
            rule_json=rule.rule_json,
            is_active=rule.is_active,
            created_at=rule.created_at.isoformat(),
            updated_at=rule.updated_at.isoformat()
        )
        for rule in rules
    ]


@router.get("/{rule_id}", response_model=RuleResponse)
async def get_rule(
    rule_id: str,
    db: Session = Depends(get_db)
):
    """Fetch a specific rule by ID."""
    engine = RuleEngine(db)
    rule = engine.get_rule(rule_id)
    
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rule {rule_id} not found"
        )
    
    return RuleResponse(
        id=str(rule.id),
        name=rule.name,
        description=rule.description,
        rule_json=rule.rule_json,
        is_active=rule.is_active,
        created_at=rule.created_at.isoformat(),
        updated_at=rule.updated_at.isoformat()
    )


@router.post("/evaluate", response_model=EvaluationResult)
async def evaluate_event(
    request: EvaluateEventRequest,
    db: Session = Depends(get_db)
):
    """
    Evaluate an event against rules and trigger actions.
    
    This is the core endpoint that:
    1. Evaluates event data against all active rules (or specific rule)
    2. Executes actions for matching rules (e.g., credit rewards)
    3. Returns detailed results of evaluation
    
    **Example Event Data:**
    ```json
    {
        "event_id": "evt_123",
        "referrer_id": "user_456",
        "referrer": {"is_paid_user": true},
        "referred": {"subscription_status": "active"}
    }
    ```
    """
    engine = RuleEngine(db)
    
    result = engine.evaluate_event(
        event_data=request.event_data,
        rule_id=request.rule_id
    )
    
    return EvaluationResult(**result)


@router.post("/seed-examples", status_code=status.HTTP_201_CREATED)
async def seed_example_rules(db: Session = Depends(get_db)):
    """Seed database with example rules for testing."""
    engine = RuleEngine(db)
    
    created_rules = []
    for example in EXAMPLE_RULES:
        rule = engine.create_rule(
            name=example["name"],
            description=example["description"],
            rule_json=example["rule_json"]
        )
        created_rules.append({
            "id": str(rule.id),
            "name": rule.name
        })
    
    return {
        "message": f"Created {len(created_rules)} example rules",
        "rules": created_rules
    }


@router.post("/nl-to-rule", response_model=RuleResponse, status_code=status.HTTP_201_CREATED)
async def natural_language_to_rule(
    request: NaturalLanguageRequest,
    db: Session = Depends(get_db)
):
    """
    🤖 **BONUS FEATURE**: Convert natural language to rule JSON using AI.
    
    Uses Google's Gemini API to convert natural language descriptions
    into structured rule JSON format.
    
    **Example Request:**
    ```json
    {
        "description": "Reward $50 when a paid user refers 3 active subscribers",
        "rule_name": "Paid User Triple Referral Bonus"
    }
    ```
    
    **Example Response:**
    ```json
    {
        "id": "uuid-here",
        "name": "Paid User Triple Referral Bonus",
        "description": "Reward $50 when a paid user refers 3 active subscribers",
        "rule_json": {
            "conditions": [
                {"field": "referrer.is_paid_user", "operator": "==", "value": true},
                {"field": "referral_count", "operator": ">=", "value": 3}
            ],
            "actions": [
                {"type": "credit", "user": "referrer_id", "amount_cents": 5000, "reward_id": "triple_referral"}
            ],
            "logic": "AND"
        }
    }
    ```
    
    **Requirements:**
    - `GEMINI_API_KEY` environment variable must be set
    - Get your free API key from: https://makersuite.google.com/app/apikey
    
    **Note:** This is an optional bonus feature demonstrating AI integration.
    The generated rule JSON is automatically validated and saved to the database.
    """
    try:
        # Initialize AI service
        ai_service = AIService()
        
        # Convert natural language to rule
        rule_data = ai_service.natural_language_to_rule(
            description=request.description,
            rule_name=request.rule_name
        )
        
        # Create the rule in database
        engine = RuleEngine(db)
        rule = engine.create_rule(
            name=rule_data["name"],
            description=rule_data["description"],
            rule_json=rule_data["rule_json"]
        )
        
        return RuleResponse(
            id=str(rule.id),
            name=rule.name,
            description=rule.description,
            rule_json=rule.rule_json,
            is_active=rule.is_active,
            created_at=rule.created_at.isoformat(),
            updated_at=rule.updated_at.isoformat()
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"AI service not configured: {str(e)}. Set GEMINI_API_KEY environment variable."
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate rule: {str(e)}"
        )



# ============================================================================
# SCHEMAS
# ============================================================================

class RuleCondition(BaseModel):
    """Schema for a rule condition."""
    field: str = Field(..., description="Field path to evaluate (e.g., 'user.is_paid')")
    operator: str = Field(..., description="Comparison operator: ==, !=, >, <, >=, <=, in, contains")
    value: Any = Field(..., description="Expected value")


class RuleAction(BaseModel):
    """Schema for a rule action."""
    type: str = Field(..., description="Action type: credit, debit, etc.")
    user: str = Field("user_id", description="Field name for user ID in event data")
    amount_cents: int = Field(..., gt=0, description="Amount in cents")
    reward_id: str = Field(..., description="Reward identifier")


class RuleJSON(BaseModel):
    """Schema for rule definition."""
    conditions: List[RuleCondition]
    actions: List[RuleAction]
    logic: str = Field("AND", description="Logic to combine conditions: AND or OR")


class CreateRuleRequest(BaseModel):
    """Request to create a new rule."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    rule_json: RuleJSON


class RuleResponse(BaseModel):
    """Response schema for a rule."""
    id: str
    name: str
    description: Optional[str]
    rule_json: Dict[str, Any]
    is_active: int
    created_at: str
    updated_at: str


class EvaluateEventRequest(BaseModel):
    """Request to evaluate an event against rules."""
    event_data: Dict[str, Any] = Field(..., description="Event data to evaluate")
    rule_id: Optional[str] = Field(None, description="Optional: Evaluate against specific rule")


class EvaluationResult(BaseModel):
    """Result of event evaluation."""
    event_data: Dict[str, Any]
    rules_evaluated: int
    rules_triggered: int
    results: List[Dict[str, Any]]


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/", response_model=RuleResponse, status_code=status.HTTP_201_CREATED)
async def create_rule(
    request: CreateRuleRequest,
    db: Session = Depends(get_db)
):
    """
    Create a new referral rule.
    
    Rules consist of:
    - **Conditions**: Field comparisons that must be met
    - **Actions**: Operations to execute when conditions match
    - **Logic**: How to combine conditions (AND/OR)
    """
    engine = RuleEngine(db)
    
    rule = engine.create_rule(
        name=request.name,
        description=request.description,
        rule_json=request.rule_json.model_dump()
    )
    
    return RuleResponse(
        id=str(rule.id),
        name=rule.name,
        description=rule.description,
        rule_json=rule.rule_json,
        is_active=rule.is_active,
        created_at=rule.created_at.isoformat(),
        updated_at=rule.updated_at.isoformat()
    )


@router.get("/", response_model=List[RuleResponse])
async def get_rules(
    active_only: bool = True,
    db: Session = Depends(get_db)
):
    """Fetch all rules."""
    engine = RuleEngine(db)
    rules = engine.get_rules(active_only=active_only)
    
    return [
        RuleResponse(
            id=str(rule.id),
            name=rule.name,
            description=rule.description,
            rule_json=rule.rule_json,
            is_active=rule.is_active,
            created_at=rule.created_at.isoformat(),
            updated_at=rule.updated_at.isoformat()
        )
        for rule in rules
    ]


@router.get("/{rule_id}", response_model=RuleResponse)
async def get_rule(
    rule_id: str,
    db: Session = Depends(get_db)
):
    """Fetch a specific rule by ID."""
    engine = RuleEngine(db)
    rule = engine.get_rule(rule_id)
    
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rule {rule_id} not found"
        )
    
    return RuleResponse(
        id=str(rule.id),
        name=rule.name,
        description=rule.description,
        rule_json=rule.rule_json,
        is_active=rule.is_active,
        created_at=rule.created_at.isoformat(),
        updated_at=rule.updated_at.isoformat()
    )


@router.post("/evaluate", response_model=EvaluationResult)
async def evaluate_event(
    request: EvaluateEventRequest,
    db: Session = Depends(get_db)
):
    """
    Evaluate an event against rules and trigger actions.
    
    This is the core endpoint that:
    1. Evaluates event data against all active rules (or specific rule)
    2. Executes actions for matching rules (e.g., credit rewards)
    3. Returns detailed results of evaluation
    
    **Example Event Data:**
    ```json
    {
        "event_id": "evt_123",
        "referrer_id": "user_456",
        "referrer": {"is_paid_user": true},
        "referred": {"subscription_status": "active"}
    }
    ```
    """
    engine = RuleEngine(db)
    
    result = engine.evaluate_event(
        event_data=request.event_data,
        rule_id=request.rule_id
    )
    
    return EvaluationResult(**result)


@router.post("/seed-examples", status_code=status.HTTP_201_CREATED)
async def seed_example_rules(db: Session = Depends(get_db)):
    """Seed database with example rules for testing."""
    engine = RuleEngine(db)
    
    created_rules = []
    for example in EXAMPLE_RULES:
        rule = engine.create_rule(
            name=example["name"],
            description=example["description"],
            rule_json=example["rule_json"]
        )
        created_rules.append({
            "id": str(rule.id),
            "name": rule.name
        })
    
    return {
        "message": f"Created {len(created_rules)} example rules",
        "rules": created_rules
    }
