"""
AI Service for Natural Language to Rule JSON Conversion

Uses Google's Gemini API to convert natural language descriptions
into structured rule JSON format.

Example:
    Input: "Reward $50 when a paid user refers 3 active subscribers"
    Output: {
        "conditions": [
            {"field": "referrer.is_paid_user", "operator": "==", "value": true},
            {"field": "referral_count", "operator": ">=", "value": 3},
            {"field": "referred.subscription_status", "operator": "==", "value": "active"}
        ],
        "actions": [
            {"type": "credit", "user": "referrer_id", "amount_cents": 5000, "reward_id": "referral_bonus"}
        ],
        "logic": "AND"
    }
"""
import json
import os
from typing import Dict, Any, Optional
import google.generativeai as genai
from fastapi import HTTPException, status


class AIService:
    """Service for AI-powered rule generation using Gemini."""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize AI service with Gemini API key.
        
        Args:
            api_key: Gemini API key (defaults to GEMINI_API_KEY env var)
        """
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        
        if not self.api_key:
            raise ValueError(
                "Gemini API key not found. Set GEMINI_API_KEY environment variable "
                "or pass api_key to constructor."
            )
        
        # Configure Gemini
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-pro')
    
    def natural_language_to_rule(
        self, 
        description: str,
        rule_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Convert natural language description to rule JSON.
        
        Args:
            description: Natural language rule description
            rule_name: Optional name for the rule
        
        Returns:
            Dictionary with rule JSON structure
        
        Raises:
            HTTPException: If API call fails or response is invalid
        
        Example:
            >>> service = AIService()
            >>> rule = service.natural_language_to_rule(
            ...     "Reward $50 when paid users refer active subscribers"
            ... )
            >>> print(rule['rule_json']['actions'][0]['amount_cents'])
            5000
        """
        # Construct prompt for Gemini
        prompt = self._build_prompt(description)
        
        try:
            # Call Gemini API
            response = self.model.generate_content(prompt)
            
            # Extract JSON from response
            rule_json = self._extract_json_from_response(response.text)
            
            # Validate the structure
            self._validate_rule_json(rule_json)
            
            # Build complete rule
            result = {
                "name": rule_name or self._generate_rule_name(description),
                "description": description,
                "rule_json": rule_json
            }
            
            return result
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"AI service error: {str(e)}"
            )
    
    def _build_prompt(self, description: str) -> str:
        """Build prompt for Gemini API."""
        return f"""You are an expert at converting natural language business rules into structured JSON format for a referral reward system.

Convert this rule description into JSON format:
"{description}"

The JSON must follow this exact structure:
{{
  "conditions": [
    {{"field": "path.to.field", "operator": "==|!=|>|<|>=|<=|in|contains", "value": any}}
  ],
  "actions": [
    {{"type": "credit|debit", "user": "user_field_name", "amount_cents": integer, "reward_id": "string"}}
  ],
  "logic": "AND|OR"
}}

Rules for conversion:
1. **Conditions**: Extract all conditions from the description
   - Common fields: referrer.is_paid_user, referred.subscription_status, referral_count, purchase.amount_cents, user.tier
   - Operators: == (equals), != (not equals), > < >= <= (comparisons), in (list membership), contains (string contains)
   - Values: true/false for booleans, numbers for amounts/counts, strings for status/tier

2. **Actions**: Extract reward actions
   - Type: "credit" for giving rewards, "debit" for taking
   - User: "referrer_id" for the referrer, "referred_id" for referred user, "user_id" for general
   - Amount in cents: $1 = 100 cents, $50 = 5000 cents, $100 = 10000 cents
   - Reward ID: descriptive string like "referral_bonus", "purchase_bonus"

3. **Logic**: "AND" if all conditions must match, "OR" if any condition can match

Examples:

Input: "Reward $50 when a paid user refers someone who subscribes"
Output:
{{
  "conditions": [
    {{"field": "referrer.is_paid_user", "operator": "==", "value": true}},
    {{"field": "referred.subscription_status", "operator": "==", "value": "active"}}
  ],
  "actions": [
    {{"type": "credit", "user": "referrer_id", "amount_cents": 5000, "reward_id": "referral_bonus"}}
  ],
  "logic": "AND"
}}

Input: "Give ₹200 bonus when referred user makes first purchase over ₹1000"
Output:
{{
  "conditions": [
    {{"field": "purchase.is_first", "operator": "==", "value": true}},
    {{"field": "purchase.amount_cents", "operator": ">", "value": 100000}}
  ],
  "actions": [
    {{"type": "credit", "user": "referrer_id", "amount_cents": 20000, "reward_id": "first_purchase_bonus"}}
  ],
  "logic": "AND"
}}

Now convert the rule and return ONLY the JSON, no explanations:"""
    
    def _extract_json_from_response(self, response_text: str) -> Dict[str, Any]:
        """Extract and parse JSON from Gemini response."""
        # Remove markdown code blocks if present
        text = response_text.strip()
        
        # Remove ```json and ``` markers
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        
        if text.endswith("```"):
            text = text[:-3]
        
        text = text.strip()
        
        # Parse JSON
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            # Try to find JSON object in the text
            start = text.find('{')
            end = text.rfind('}') + 1
            
            if start >= 0 and end > start:
                try:
                    return json.loads(text[start:end])
                except json.JSONDecodeError:
                    pass
            
            raise ValueError(f"Could not parse JSON from response: {e}")
    
    def _validate_rule_json(self, rule_json: Dict[str, Any]) -> None:
        """Validate that rule JSON has correct structure."""
        required_keys = ["conditions", "actions", "logic"]
        
        for key in required_keys:
            if key not in rule_json:
                raise ValueError(f"Missing required key: {key}")
        
        if not isinstance(rule_json["conditions"], list):
            raise ValueError("conditions must be a list")
        
        if not isinstance(rule_json["actions"], list):
            raise ValueError("actions must be a list")
        
        if rule_json["logic"] not in ["AND", "OR"]:
            raise ValueError("logic must be 'AND' or 'OR'")
        
        # Validate conditions
        for i, condition in enumerate(rule_json["conditions"]):
            if not isinstance(condition, dict):
                raise ValueError(f"Condition {i} must be a dict")
            
            if "field" not in condition or "operator" not in condition or "value" not in condition:
                raise ValueError(f"Condition {i} missing required keys")
        
        # Validate actions
        for i, action in enumerate(rule_json["actions"]):
            if not isinstance(action, dict):
                raise ValueError(f"Action {i} must be a dict")
            
            if "type" not in action or "user" not in action or "amount_cents" not in action:
                raise ValueError(f"Action {i} missing required keys")
    
    def _generate_rule_name(self, description: str) -> str:
        """Generate a rule name from description."""
        # Take first 50 chars and clean up
        name = description[:50].strip()
        if len(description) > 50:
            name += "..."
        return name


# Example usage
if __name__ == "__main__":
    # Test the service
    service = AIService()
    
    test_cases = [
        "Reward $50 when a paid user refers someone who subscribes",
        "Give ₹200 bonus when referred user makes first purchase over ₹1000",
        "Credit $100 if user completes 5 referrals and all are active",
    ]
    
    for description in test_cases:
        print(f"\n📝 Input: {description}")
        
        try:
            rule = service.natural_language_to_rule(description)
            print(f"✅ Generated Rule:")
            print(json.dumps(rule, indent=2))
        except Exception as e:
            print(f"❌ Error: {e}")
