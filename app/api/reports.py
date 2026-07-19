from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def list_reports():
    return {"reports": [], "message": "Reports endpoint - not yet implemented"}
