from fastapi import FastAPI

from app.routers import auth, itineraries, trips, users, voice


app = FastAPI(title="AI_Vacation_Planner")

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(trips.router)
app.include_router(itineraries.router)
app.include_router(voice.router)
