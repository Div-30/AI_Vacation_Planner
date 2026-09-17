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

PLACE_CATEGORIES: dict[str, str] = {
    "restaurant": "amenity=restaurant",
    "cafe": "amenity=cafe",
    "attraction": "tourism=attraction",
    "museum": "tourism=museum",
    "hotel": "tourism=hotel",
    "park": "leisure=park",
}

@tool
def find_places(destination: str, category: str = "attraction") -> str:
    """Find real points of interest near a destination. Use `category` to narrow
        results: 'restaurant', 'cafe', 'attraction', 'museum', 'hotel', or 'park'."""
    try:
        geo_response = httpx.get(
            f"https://geocoding-api.open-meteo.com/v1/search?name={destination}&count=1"
        )
        geo_data = geo_response.json()
        if not geo_data.get("results"):
            return f"Could not find weather data for {destination}."
        location = geo_data["results"][0]
        lat, lon = location["latitude"], location["longitude"]

        key, value = PLACE_CATEGORIES.get(category, PLACE_CATEGORIES["attraction"]).split("=")
        overpass_query = f'[out:json];node["{key}"="{value}"](around:3000,{lat},{lon});out 10;' 
        places_response = httpx.post(
            "https://overpass-api.de/api/interpreter",
            data={"data": overpass_query},
        )
        elements = places_response.json().get("elements", [])
        names = [el["tags"]["name"] for el in elements if el.get("tags", {}).get("name")]
        if not names:
            return f"No named {category} found near {destination}."
        return f"{category.title()}s near {destination}: " + ", ".join(names[:10])
    except Exception:
        return f"Failed to featch places for {destination}"

@tool
def get_route(origin: str, destination: str) -> str:
    """Get the travel distance and estimate driving time between two locations (e.g: a hotel and an attraction, or two cities)."""
    try:
        def geocode(place: str) -> tuple[float, float]:
            response = httpx.get(
                f"https://geocoding-api.open-meteo.com/v1/search?name={place}&count=1"
            )
            result = response.json()["result"][0]
            return result["longitude"], result["latitude"]
        
        origin_lon, origin_lat = geocode(origin)
        dest_lon, dest_lat = geocode(destination)

        route_response = httpx.get(
            f"http://router.project-osrm.org/route/v1/driving/"
            f"{origin_lon},{origin_lat};{dest_lon},{dest_lat}?overview=false"
        )
        route_data = route_response.json()
        if route_data.get("code") != "Ok":
            return f"Could not calculate a route from {origin} to {destination}."
        route = route_data["routes"][0]
        distance_km = route["distance"] / 1000
        duration_min = route["duration"] / 60
        return(
            f"Route from {origin} to {destination}: {distance_km:.1f} km, "
            f"approx. {duration_min:.0f} min by car"
        )
    except Exception:
        return f"Failed to calculate route from {origin} to {destination}"

SAVE_ITINERARY_TOOL = {
    "name": "save_itinerary",
    "description": (
        "Save the fully generated itinerary in a structured format. Call this once."
        "you are done gathering information and are ready to finalize the trip plan."
    ),
    "input_schema": models.ItineraryLLMOutput.model_json_schema(),
}
RUNTIME_TOOLS = [get_weather, search_travel_knowledge, find_places, get_route]
ALL_TOOLS = [*RUNTIME_TOOLS, SAVE_ITINERARY_TOOL]