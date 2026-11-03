from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError

import httpx

mcp = FastMCP("travel_tools")

PLACE_CATEGORIES: dict[str, str] = {
    "restaurant": "amenity=restaurant",
    "cafe": "amenity=cafe",
    "attraction": "tourism=attraction",
    "museum": "tourism=museum",
    "hotel": "tourism=hotel",
    "park": "leisure=park",
}

@mcp.tool()
def get_weather(destination: str) -> str:
    """ Get the weather and forecast for a destination city, to tailor
        activities (indoor vs outdoor) to expected conditions."""
    try:
        geo_response = httpx.get(
            f"https://geocoding-api.open-meteo.com/v1/search?name={destination}&count=1"
        )
        geo_response.raise_for_status()
        geo_data = geo_response.json()
        if not geo_data.get("results"):
            return f"Could not find weather data for {destination}."
        location = geo_data["results"][0]
        weather_response = httpx.get(
            "https://api.open-meteo.com/v1/forecast"
            f"?latitude={location['latitude']}&longitude={location['longitude']}&current_weather=true"
        )
        weather_response.raise_for_status()
        current = weather_response.json()["current_weather"]
        return (
            f"The current weather in {destination} is {current['temperature']}°C"
            f"with wind speeds of {current['windspeed']} km/h"
        )
    except httpx.HTTPError as e:
        raise ToolError(f"Weather prpvider error for {destination}: {e}")

@mcp.tool()
def find_places(destination: str, category: str = "attraction") -> str:
    """Find real points of interest near a destination. Use `category` to narrow
        results: 'restaurant', 'cafe', 'attraction', 'museum', 'hotel', or 'park'."""
    try:
        geo_response = httpx.get(
            f"https://geocoding-api.open-meteo.com/v1/search?name={destination}&count=1"
        )
        geo_response.raise_for_status()
        geo_data = geo_response.json()
        if not geo_data.get("results"):
            return f"Could not find location data for {destination}."
        location = geo_data["results"][0]
        lat, lon = location["latitude"], location["longitude"]

        key, value = PLACE_CATEGORIES.get(category, PLACE_CATEGORIES["attraction"]).split("=")
        overpass_query = f'[out:json];node["{key}"="{value}"](around:3000,{lat},{lon});out 10;' 
        places_response = httpx.post(
            "https://overpass-api.de/api/interpreter",
            data={"data": overpass_query},
        )
        places_response.raise_for_status()
        elements = places_response.json().get("elements", [])
        names = [el["tags"]["name"] for el in elements if el.get("tags", {}).get("name")]
        if not names:
            return f"No named {category} found near {destination}."
        return f"{category.title()} is near {destination}: " + ", ".join(names[:10])
    except httpx.HTTPError as e:
        raise (f"Places provider error for {destination}: {e}")

@mcp.tool()
def get_route(origin: str, destination: str) -> str:
    """Get the travel distance and estimate driving time between two locations (e.g: a hotel and an attraction, or two cities)."""
    try:
        def geocode(place: str) -> tuple[float, float]:
            response = httpx.get(
                f"https://geocoding-api.open-meteo.com/v1/search?name={place}&count=1"
            )
            response.raise_for_status()
            results = response.json().get("results")
            if not results:
                return None
            return results[0]["longitude"], results[0]["latitude"]
        
        origin_coords = geocode(origin)
        if not origin_coords:
            return f"Could not find location data for origin: {origin}"

        dest_coords = geocode(destination)
        if not dest_coords:
            return f"Could not find location data for destination: {destination}"

        route_response = httpx.get(
            f"http://router.project-osrm.org/route/v1/driving/"
            f"{origin_coords[0]},{origin_coords[1]};{dest_coords[0]},{dest_coords[1]}?overview=false"
        )
        route_response.raise_for_status()
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
    except httpx.HTTPError as e:
        raise ToolError(F"Routing provider error: {e}")

if __name__ == "__main__":
    mcp.run(transport="stdio")