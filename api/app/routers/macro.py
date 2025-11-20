from fastapi import APIRouter

router = APIRouter()

@router.get("/")
def macro(region: str = "US") -> dict:
    # Stub — T4
    return {"region": region, "series": []}
