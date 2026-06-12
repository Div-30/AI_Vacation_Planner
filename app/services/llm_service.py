import json
from anthropic import Anthropic
from app.config import settings
from app import models

client = Anthropic(api_key=settings.anthropic_api_key)
MODEL_NAME = "claude-3-haiku-20240307"
def generate_itinerary_json(trip: models.Trip) -> dict:
    """
    Takes a Trip database model, injects its data into the engineered prompt, calls Claude, and returns the parsed JSON dictionary.
    """
    prompt = f"""
You are an expert, local travel agent. Plan a highly realistic {trip.days}-day itinerary for a trip to {trip.destination}.
Strict Constraints:
1. Budget: The total cost must strictly align with a '{trip.budget}' budget tier. Suggest realistic activities, transport, and dining that fit this constraint.
2. Geography: All suggested locations, restaurants and activities MUST be physically located within {trip.destination} or a highly accessible travel distance. Do not hallucinate locations.
3. Travel style: Tailor the activities, pacing, and recommendations entirely to a '{trip.trip_style}' travel style.

Output Format:
Return ONLY a valid JSON object representing the daily itinerary. Do not include markdown formatting, code blocks, conversational text, or explanations. Follow this exact schema:
{{
  "destination": "{trip.destination}",
  "total_days" : {trip.days},
  "itinerary": [
  {{
    "day_number: 1,
    "theme_or_focus: "...",
    "activities": [
      {{"time": "Morning", "description": "...", "location": "..."}}
      {{"time": "Afternoon", "description": "...", "location": "..."}}
    ],
    "estimated_daily_cost": "..."
  }}
  ]
}}
"""
    messages = [
        {"role": "user", "content": prompt}
    ]

    response = client.messages.create(
        model=MODEL_NAME,
        max_tokens=2500,
        messages=messages
    )

    raw_json_string = response.content[0].text

    return json.loads(raw_json_string)