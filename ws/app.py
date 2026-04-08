from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import router
from .service import ComDigitalScalesService


def create_app(
    digital_scales_executor,
    digital_scales_driver,
    app_service,
):
    app = FastAPI()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )


    app.state.digital_scales_service = ComDigitalScalesService(
        digital_scales_executor,
        digital_scales_driver,
    )
    app.state.app_service = app_service

    app.include_router(router)

    return app
