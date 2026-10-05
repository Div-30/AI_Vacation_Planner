from langchain_core.tools import tool


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


@tool("save_itinerary", args_schema=models.ItineraryLLMOutput)
def save_itinerary_tool(**kwargs) -> str:
    """Save the fully generated itinerary in a structured format. Call this once
    you are done gathering information and are ready to finalize the trip plan."""
    return "saved"
NATIVE_TOOLS = [search_travel_knowledge]