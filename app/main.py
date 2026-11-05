from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.agent.graph import init_itinerary_graph
from app.routers import auth, itineraries, trips, users, voice

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_itinerary_graph()
    yield

app = FastAPI(title="AI_Vacation_Planner", lifespan=lifespan)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(trips.router)
app.include_router(itineraries.router)
app.include_router(voice.router)