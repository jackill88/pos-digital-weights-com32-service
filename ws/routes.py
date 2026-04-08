import logging
import sqlite3
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request

from .models import (
    DigitalScaleUploadRequest,
)
from .service import (
    ComDigitalScalesService,
)

API_KEY = "your-secret"

router = APIRouter()

logger = logging.getLogger(__name__)



def validate_api_key(
    request: Request,
    x_api_key: str = Header(None)
):
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing API key (x-api-key)")

    service = request.app.state.app_service

    if not service.validate_api_key(x_api_key):
        raise HTTPException(status_code=401, detail="Invalid API key")



def get_digital_scales_service(request: Request) -> ComDigitalScalesService:
    return request.app.state.digital_scales_service


def ensure_digital_scales_configured(service: ComDigitalScalesService):
    if not service or not service.is_configured():
        raise HTTPException(
            status_code=503,
            detail="Digital scales integration is not configured",
        )


@router.get("/health")
async def health(
    _=Depends(validate_api_key),
    x_api_key: str = Header(None),
    service: ComDigitalScalesService = Depends(get_digital_scales_service),
):
    result = await service.health()
    return {"result": result}


@router.post("/digital-scales/connect")
async def digital_scales_connect(
    _=Depends(validate_api_key),
    x_api_key: str = Header(None),
    service: ComDigitalScalesService = Depends(get_digital_scales_service),
):
    ensure_digital_scales_configured(service)

    try:
        result = await service.connect()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    return {"result": result}


@router.post("/digital-scales/disconnect")
async def digital_scales_disconnect(
    _=Depends(validate_api_key),
    x_api_key: str = Header(None),
    service: ComDigitalScalesService = Depends(get_digital_scales_service),
):
    ensure_digital_scales_configured(service)

    try:
        result = await service.disconnect()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    return {"result": result}


@router.get("/digital-scales/health")
async def digital_scales_health(
    _=Depends(validate_api_key),
    x_api_key: str = Header(None),
    service: ComDigitalScalesService = Depends(get_digital_scales_service),
):
    ensure_digital_scales_configured(service)

    try:
        result = await service.health()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    return {"result": result}


@router.post("/digital-scales/clear")
async def digital_scales_clear(
    _=Depends(validate_api_key),
    x_api_key: str = Header(None),
    service: ComDigitalScalesService = Depends(get_digital_scales_service),
):
    ensure_digital_scales_configured(service)

    try:
        result = await service.clear_database()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    return {"result": result}


@router.get("/digital-scales/version")
async def digital_scales_version(
    _=Depends(validate_api_key),
    x_api_key: str = Header(None),
    service: ComDigitalScalesService = Depends(get_digital_scales_service),
):
    ensure_digital_scales_configured(service)

    try:
        result = await service.version()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    return {"result": result}


@router.post("/digital-scales/upload")
async def digital_scales_upload(
    payload: DigitalScaleUploadRequest,
    _=Depends(validate_api_key),
    x_api_key: str = Header(None),
    service: ComDigitalScalesService = Depends(get_digital_scales_service),
):
    ensure_digital_scales_configured(service)

    try:
        result = await service.upload_products(payload.items, payload.partial)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    return {"result": result}
