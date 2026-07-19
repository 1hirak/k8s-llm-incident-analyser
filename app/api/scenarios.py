from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def list_scenarios():
    scenarios = [
        "01-missing-env",
        "02-db-unavailable",
        "03-crashloop",
        "04-imagepull",
        "05-oom",
        "06-readiness",
        "07-liveness",
        "08-bad-configmap",
        "09-app-exception",
        "10-wrong-port",
    ]
    return {"scenarios": scenarios}
