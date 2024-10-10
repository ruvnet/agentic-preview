from fastapi import APIRouter

router = APIRouter()

@router.get("/status/{app_name}")
async def get_status(app_name: str):
    # Your existing status check logic here
    pass
