from json import tool

import httpx


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