from app import models
from app.agent.graph import get_itinerary_graph


async def generate_itinerary_json(trip: models.Trip) -> dict:
    initial_state = {
        "messages": [],
        "destination": trip.destination,
        "days": trip.days,
        "budget": trip.budget,
        "trip_style": trip.trip_style,
        "itinerary": None,
    }
    itinerary_graph = get_itinerary_graph()
    result = await itinerary_graph.ainvoke(initial_state)

    if not result.get("itinerary"):
        raise ValueError("LLM failed to output a structured itinerary via tools.")
    
    return result["itinerary"]


