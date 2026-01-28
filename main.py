"""Entry file for Bus tracker API"""

from fastapi import FastAPI, APIRouter
from app.routers.test import router as test_endpoint
from app.routers.Journey import router as journey_endpoint
from app.routers.Route import router as routes_endpoint

app = FastAPI()

#app.include_router(test_endpoint)
app.include_router(journey_endpoint)
app.include_router(routes_endpoint)

@app.get("/health")
def health():
    return {"200"}
