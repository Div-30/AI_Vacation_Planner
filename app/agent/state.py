from typing import Annotated, Optional, TypedDict
from langchain_core.messages import AnyMessage
from langgraph.graph import add_messages


class ItineraryAgentState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    destination: str
    days: int
    budget: int
    trip_style: str
    itinerary: Optional[dict]