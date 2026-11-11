import logging

from app import models
from app.agent.graph import get_itinerary_graph
from app.agent.observability import AgentObservabilityCallback

logger = logging.getLogger(__name__)

async def generate_itinerary_json(trip: models.Trip) -> dict:
    initial_state = {
        "messages": [],
        "destination": trip.destination,
        "days": trip.days,
        "budget": trip.budget,
        "trip_style": trip.trip_style,
        "itinerary": None,
    }
    observer = AgentObservabilityCallback()
    config = {"callbacks": [observer]}
    itinerary_graph = get_itinerary_graph()
    result = await itinerary_graph.ainvoke(initial_state, config=config)

    try:
        from ddtrace.llmobs import LLMObs
        if LLMObs.enabled:
            LLMObs.flush()
    except Exception:
        pass

    summary = observer.get_summary()
    logger.info(f"Agent Execution Observability Summary: {summary}")

    if not result.get("itinerary"):
        raise ValueError(f"LLM failed to output a structured itinerary. Errors: {summary['errors']}")
    
    return result["itinerary"]


