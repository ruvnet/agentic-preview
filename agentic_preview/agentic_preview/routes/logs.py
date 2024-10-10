from fastapi import APIRouter

router = APIRouter()

@router.get("/logs/{app_name}")
async def stream_logs(app_name: str):
    # Your existing log streaming logic here
    pass
