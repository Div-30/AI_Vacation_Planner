from app.knowledge_base.context_assembler import assemble_context_for_destination
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
        "input_schema": models.ItineraryLLMOutput.model_json_schema()
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
    knowledge_context = assemble_context_for_destination(trip.destination)
    prompt = f"""{knowledge_context}
Plan a highly realistic {trip.days}-day itinerary for a trip to {trip.destination}.
Strict Constraints:
1. Budget: The total cost must strictly align with a '{trip.budget}' budget tier. Suggest realistic activities, transport, and dining that fit this constraint.
2. Geography: All suggested locations, restaurants and activities MUST be physically located within {trip.destination} or a highly accessible travel distance. Do not hallucinate locations.
3. Travel style: Tailor the activities, pacing, and recommendations entirely to a '{trip.trip_style}' travel style.
4. Knowledge Base: Where relevant, incorporate the specific local tips, hidden gems and recommendations from the travel knowledge base provided above.
Process:
1. Call `get_weather` to get the weather for {trip.destination}.
2. Then, call `save_itinerary` to output the final plan.
"""
    messages = [
        {"role": "user", "content": prompt}
    ]
    MAX_ITERATIONS = 5  
    for _ in range(MAX_ITERATIONS): 
        response = client.messages.create(
            model=MODEL_NAME,
            system= SYSTEM_PROMPT,
            max_tokens=3000,
            tools=TOOLS,
            messages=messages,
            tool_choice={"type": "any"}
        )
        if response.stop_reason != "tool_use":
            raise ValueError("LLM failed to output a structured itinerary via tools.")
        messages.append({"role": "assistant", "content": response.content})

        tool_results= []
        for block in response.content:
            if block.type == "tool_use":
                if block.name == "save_itinerary":
                    return block.input
                else:
                    result_text = _execute_tool(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result_text,
                    })
        if tool_results:
            messages.append({"role": "user", "content": tool_results})
            
    raise ValueError("LLM exceeded the maximum number of tool call iterations without producing an itinerary.")


