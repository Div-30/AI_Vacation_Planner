from fastapi import FastAPI

from app.routers import auth, itineraries, trips


app = FastAPI(title="AI_Vacation_Planner")

app.include_router(auth.router)
app.include_router(trips.router)
app.include_router(itineraries.router)