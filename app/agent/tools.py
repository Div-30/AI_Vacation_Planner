from json import tool

import httpx

from app import models
from app.knowledge_base.retrieval import retrieve_relevant_context


@tool
def get_weather(destination: str) -> str:
    """ Get the weather and forecast for a destination city, to tailor
        activities (indoor vs outdoor) to expected conditions."""
    try:
        geo_response = httpx.get(
            f"https://geocoding-api.open-meteo.com/v1/search?name={destination}&count=1"
        )
        geo_data = geo_response.json()
        if not geo_data.get("results"):
            return f"Could not find weather data for {destination}."
        location = geo_data["results"][0]
        weather_response = httpx.get(
            "https://api.open-meteo.com/v1/forecast"
            f"?latitude={location['latitude']}&longitude={location['longitude']}&current_weather=true"
        )
        current = weather_response.json()["current_weather"]
        return (
            f"The current weather in {destination} is {current['temperature']}°C"
            f"with wind speeds of {current['windspeed']} km/h"
        )
    except Exception:
        return f"Failed to fetch weather for {destination}"

@tool
def search_travel_knowledge(destination: str, topic: str = "general travel tips, highlights, and recommandations") -> str:
    """Search the curated local travel knowledge base for a destination.
    Narrow the search with `topic` (e.g. 'food', 'safety', 'hidden gems', 'transportation', 'pricing')
    when you need something more specific than general tips."""
    results = retrieve_relevant_context(
        query=f"{topic} for {destination}",
        destination=destination,
        limit=5,
    )
    if not results:
        return f"No curated travel knowledge found for {destination}"
    return "\n\n".join(
        f"[{chunk.get('doc_type', 'general').replace('_', ' ').title()}] {chunk['content']}"
        for chunk in results
    )

SAVE_ITINERARY_TOOL = {
    "name": "save_itinerary",
    "description": (
        "Save the fully generated itinerary in a structured format. Call this once."
        "you are done gathering information and are ready to finalize the trip plan."
    ),
    "input_schema": models.ItineraryLLMOutput.model_json_schema(),
}
RUNTIME_TOOLS = [get_weather, search_travel_knowledge]
ALL_TOOLS = [*RUNTIME_TOOLS, SAVE_ITINERARY_TOOL]