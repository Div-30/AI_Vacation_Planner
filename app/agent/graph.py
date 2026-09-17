from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END

from app.agent.state import ItineraryAgentState
from app.agent.tools import ALL_TOOLS
from app.config import settings


MODEL_NAME = "claude-haiku-4-5"

SYSTEM_PROMPT = """You are an expert, local travel agent responsible for building highly realistic, structured travel itineraries.

You have access to the following tools:
- get_weather: check the current weather/forecast for the destination to decide
  between indoor and outdoor activities.
- search_travel_knowledge: look up curated local tips, hidden gems, safety notes,
  or destination pricing. Use `topic` to narrow the search (e.g. 'food', 'pricing').
- find_places: find real, named points of interest (restaurants, attractions,
  museums, hotels, parks) near the destination. Never invent place names.
- get_route: check travel distance/time between two locations to keep each day's
  plan geographically realistic.
- save_itinerary: call this ONCE, as your final action, once you are done gathering
  information and are ready to submit the complete structured itinerary. Do not
  call it alongside other tools in the same turn.

Guidelines:
1. Budget: the total cost must align with the given budget tier.
2. Geography: all locations must be real and reachable within the trip; use
   find_places and get_route to verify this rather than guessing.
3. Travel style: tailor pacing and activities to the requested style.
4. Ground your plan in real data from the tools above rather than assumptions.
"""
model = ChatAnthropic(
    model = MODEL_NAME,
    api_key = settings.anthropic_api_key,
    max_token = 3000,
)
model_with_tools = model.bind_tools(ALL_TOOLS, tool_choice="any")

def call_agent(state: ItineraryAgentState) -> dict:
    new_messages = []
    if not state["messages"]:
        user_prompt = (
            f"Plan a highly realistic {state['days']}-day itinerary for a trip to "
            f"{state['destination']}.\n"
            f"Budget tier: {state['budget']}.\n"
            f"Travel style: {state['trip_style']}.\n"
            "Use your tools to check the weather, find real places, verify routes, "
            "and pull local knowledge before finalizing the plan"
        )
        new_messages.append(HumanMessage(content=user_prompt))
    conversation = [SystemMessage(content=SYSTEM_PROMPT), *state["messages"], *new_messages]
    response = model_with_tools.invoke(conversation)
    new_messages.append(response)
    return {"messages": new_messages}

def route_after_agent(state: ItineraryAgentState) -> str:
    last_message = state["messages"][-1]
    tool_calls = getattr(last_message, "tool_calls", None)
    if not tool_calls:
        return END
    for call in tool_calls:
        if call["name"] == "save_itinerary":
            return "finalize"
    return "tools"
def finalize(state: ItineraryAgentState) -> dict:
    last_message = state["messages"][-1]
    for call in last_message.tool_calls:
        if call["name"] == "save_itinerary":
            return {"itinerary": call["args"]}
    return {}
