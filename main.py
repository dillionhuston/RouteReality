"""Entry file for Bus tracker API"""

from fastapi import FastAPI, APIRouter
from app.routers.test import router as test_endpoint

app = FastAPI()

app.include_router(test_endpoint)

@app.get("/health")
def health():
    return {"200"}
