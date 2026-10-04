from app import models
from app.agent.graph import itinerary_graph


def generate_itinerary_json(trip: models.Trip) -> dict:
    initial_state = {
        "messages": [],
        "destination": trip.destination,
        "days": trip.days,
        "budget": trip.budget,
        "trip_style": trip.trip_style,
        "itinerary": None,
    }
    result = itinerary_graph.invoke(initial_state)

    if not result.get("itinerary"):
        raise ValueError("LLM failed to output a structured itinerary via tools.")
    
    return result["itinerary"]


