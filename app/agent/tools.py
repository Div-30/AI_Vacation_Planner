from langchain_core.tools import tool

import httpx

from app import models
from app.knowledge_base.retrieval import retrieve_relevant_context


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


@tool("save_itinerary", args_schema=models.ItineraryLLMOutput)
def save_itinerary_tool(**kwargs) -> str:
    """Save the fully generated itinerary in a structured format. Call this once
    you are done gathering information and are ready to finalize the trip plan."""
    return "saved"
RUNTIME_TOOLS = [get_weather, search_travel_knowledge, find_places, get_route]
ALL_TOOLS = [*RUNTIME_TOOLS, save_itinerary_tool]