from pydantic import ValidationError
import pytest

from app.models import ItineraryLLMOutput


def test_valid_itinerary_model():
    data = {
        "destination": "London",
        "total_days": 1,
        "itinerary": [
            {
                "day_number": 1,
                "theme_or_focus": "Royal London",
                "estimated_daily_cost": "$150",
                "activities": [
                    {
                        "time": "09:00",
                        "description": "Visit Buckingham Palace",
                        "location": "Buckingham Palace",
                        "duration": "2 hours",
                        "cost": "$40"
                    }
                ]
            }
        ]
    }
    validated = ItineraryLLMOutput.model_validated(data)
    assert validated.destination == "London"
    assert len(validated.itinerary) == 1
    assert validated.itinerary[0].activities[0].location == "Buckingham Palace"

def test_invalid_itinerary_model_missing_field():
    invalid_data = {
        "destination": "London",
        "total_days": 1,
        "itinerary": [
            {
                "theme_or_focus": "No day number",
                "activities": []
            }
        ]
    }
    with pytest.raises(ValidationError):
        ItineraryLLMOutput.model_validate(invalid_data)