from fastapi import FastAPI, APIRouter

router = APIRouter(prefix="/test", tags=["Test"])

router.get("/test")
def test_endpoint():
    return str("200")