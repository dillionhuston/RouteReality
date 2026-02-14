"""Entry file for Bus tracker API"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers.Journey import router as journey_endpoint
from app.routers.Route import router as routes_endpoint
from app.routers.status import router as status_endpoint

app = FastAPI(
    title="Bus Tracker API",
    description="API for managing Belfast bus journeys, routes, and related data",
    version="0.1.0"
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

@app.get("/")
async def root():
    return {"message": "Bus Tracker API is running"}

@app.get("/health")
async def health():
    return {"status": "healthy", "code": 200}