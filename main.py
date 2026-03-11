"""Entry file for Bus tracker API"""

import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers.Journey import router as journey_endpoint
from app.routers.Route import router as routes_endpoint
from app.routers.status import router as status_endpoint
from app.routers.Auth import router as auth_endpoint
from app.routers.Broadcast import router as broadcast_endpoint

from app.Services.journeyService.eventHandler import set_main_loop

app = FastAPI(
    title="Bus Tracker API",
    description="API for managing Belfast bus journeys, routes, and related data",
    version="1.3.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(journey_endpoint)
app.include_router(routes_endpoint)
app.include_router(status_endpoint)
app.include_router(auth_endpoint)
app.include_router(broadcast_endpoint)

@app.on_event("startup")
async def startup():
    app.state.loop = asyncio.get_event_loop()
    set_main_loop(asyncio.get_event_loop())  

@app.get("/")
async def root():
    return {"message": "Bus Tracker API is running"}

@app.get("/health")
async def health():
    return {"status": "healthy", "code": 200}
