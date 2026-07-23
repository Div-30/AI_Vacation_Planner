import json
from anthropic import Anthropic
from app.config import settings
from app import models
import httpx

client = Anthropic(api_key=settings.anthropic_api_key)
MODEL_NAME = "claude-haiku-4-5"
SYSTEM_PROMPT= """You are an expert, local travel agent.
Your job is to generate a highly realistic and structured itinerary.
You have two tools available:
- get_weather: use this first to get the current weather and forecast for the destination, so you can tailor activities (e.g.
  indoor vs outdoor) to the expected conditions.
- save_itinerary: use this to submit the final itinerary once you have checked the weather. This tool receives the structured
  JSON of the itinerary."""

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
    "day_number": 1,
    "theme_or_focus": "...",
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
    print(f"DEBUG - Claude Raw Response: {raw_json_string}")
    start_id = raw_json_string.find("{")
    end_id = raw_json_string.rfind("}")

    if start_id != -1 and end_id != -1:
        clean_json_string = raw_json_string[start_id:end_id + 1]
    else:
        clean_json_string = raw_json_string

    return json.loads(clean_json_string)

TOOLS = [
    {
        "name": "get_weather",
        "description": (
            "Get the current weather and forecast for a destination city to help plan the itinerary"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "destination": {"type": "string", "destination": "The city/country name"}
            },
        },
    },
]