import re
from typing import Any, Dict, List

from fastapi import HTTPException, status
from pydantic import ValidationError

from app import models


PROMPT_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior)\s+instructions",
    r"system\s*prompt",
    r"reveal\s+(the\s+)?(api[_\s]?key|secret|password)",
    r"you\s+are\s+now\s+in\s+developer\s+mode",
    r"jailbreak",
    r"DAN\s+mode",
    r"bypass\s+restrictions",
    r"as\s+an\s+ai\s+language\s+model",
]
class GuardrailsException(HTTPException):
    def __init__(self, detail: str):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)
    def validate_input_safety(destination: str, trip_style: str, days: int, budget: int) -> None:
        """Pre-execution guardrails: validates constraints and checks for prompt injections."""
        if days < 1 or days > 30:
            raise GuardrailsException(detail="Trip duration must be between 1 and 30 days.")
        if budget <= 0:
            raise GuardrailsException(detail="Trip budget must be a positive number.")

        if len(destination.strip()) < 2:
            raise GuardrailsException(detail="Destination name is too short or invalid.")
        combined_input = f"{destination}{trip_style}".lower()
        for pattern in PROMPT_INJECTION_PATTERNS:
            if re.search(pattern, combined_input):
                raise GuardrailsException(detail="Malicious prompt injection or disallowed instructions detected intrip parameters.")
        def validate_output_safety(destination: str, expected_days: int, itinerary_dict: Dict[str, Any]) -> models.ItineraryLLMOutput:
            """Post-execution guardrails: validates the LLM itinerary output completeness and safety."""
            try:
                validated = models.ItineraryLLMOutput.model_validate(itinerary_dict)
            except ValidationError as e:
                raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Guardrail Error: Model produced malformed itinerary schema: {e.errors()}")
            if len(validated.itinerary) != expected_days:
                raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Guardrail Error: Requested {expected_days} days but agent generated {len(validated.itinerary)} days.")

            for day in validated.itinerary:
                if not day.activities:
                    raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Guardrail Error: Day {day.day_number} has no scheduled activities.")
            return validated