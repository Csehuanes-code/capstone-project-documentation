from fastapi import APIRouter, Request, Response

router = APIRouter()


@router.get("/health", tags=["Operación"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": "auth"}


@router.get("/ready", tags=["Operación"])
async def readiness(request: Request, response: Response) -> dict[str, str]:
    check = request.app.state.readiness_check
    if check is None or not await check():
        response.status_code = 503
        return {"status": "not_ready", "service": "auth"}
    return {"status": "ready", "service": "auth"}
