import os
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.agent.graph import init_itinerary_graph
from app.routers import auth, itineraries, trips, users, voice

if os.getenv("DD_API_KEY"):
    try:
        from ddtrace.llmobs import LLMObs
        LLMObs.enable(
            ml_app=os.getenv("DD_LLMOBS_ML_APP", "vacation-planner-agent"),
            agentless_enabled=True,
            site=os.getenv("DD_SITE", "datadoghq.com"),
            api_key=os.getenv("DD_API_KEY"),
            service=os.getenv("DD_SERVICE", "ai-vacation-planner"),
            env=os.getenv("DD_ENV", "dev"),
        )
    except Exception as e:
        print(f"Notice: Datadog LLMObs not enabled: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_itinerary_graph()
    yield
    if os.getenv("DD_API_KEY"):
        try:
            from ddtrace.llmobs import LLMObs
            if LLMObs.enabled:
                LLMObs.flush()
        except Exception:
            pass

app = FastAPI(title="AI_Vacation_Planner", lifespan=lifespan)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(trips.router)
app.include_router(itineraries.router)
app.include_router(voice.router)