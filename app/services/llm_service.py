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
TOOLS = [
    {
        "name": "get_weather",
        "description": (
            "Get the current weather and forecast for a destination city to help plan the itinerary"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "description": {"type": "string", "destination": "The city/country name"}
            },
            "required": ["destination"]
        },
    },
    {
        "name": "save_itinerary",
        "description": "Save the fully generated itinerary in a structured format. Call this when you have gathered weather information and are ready to finalize the trip plan.",
        "input_schema": {
            "type": "object",
            "properties": {
                "destination": {"type": "string"},
                "total_days": {"type": "integer"},
                "itinerary": {"type": "array", 
                              "items": {
                                  "type": "object",
                                  "properties": {
                                      "day_number": {"type": "integer"},
                                      "theme_or_focus": {"type": "string"},
                                      "activities": {
                                          "type": "array",
                                          "items": {
                                              "type": "object",
                                              "properties": {
                                                  "time": {"type": "string"},
                                                  "description": {"type": "string"},
                                                  "location": {"type": "string"}
                                                },
                                            "required": ["time", "description", "location"]
                                        }
                                    },
                                "estimated_daily_cost": {"type": "string"}
                            },
                        "required": ["day_number", "theme_or_focus", "activities", "estimated_daily_cost"]
                    }
                }
            },
            "required": ["destination", "total_days", "itinerary"]
        }
    }
]

def get_real_weather(destination: str) -> str:
    try:
        geo_code_url = f"https://geocoding-api.open-meteo.com/v1/search?name={destination}&count=1"
        geo_response = httpx.get(geo_code_url)
        geo_data = geo_response.json()

        if not geo_data.get("results"):
            return f"Could not find weather data for {destination}."
        location = geo_data["results"][0]
        lat = location["latitude"]
        lon = location["longitude"]

        weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
        weather_response = httpx.get(weather_url)
        weather_data = weather_response.json()

        current = weather_data["current_weather"]
        temp = current["temperature"]       
        windspeed = current["windspeed"]
        return f"The current weather in {destination} is {temp}°C with wind speeds of {windspeed} km/h."
    except Exception as e:
        return f"Failed to fetch weather for {destination}."

def _execute_tool(tool_name: str, tool_input: dict) -> str:
    if tool_name == "get_weather":
        destination = tool_input.get("destination", "the destination")
        return get_real_weather(destination)
    return f"Unknown tool: {tool_name}"

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

