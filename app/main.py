from fastapi import FastAPI

from app.routers import health


def create_app() -> FastAPI:
    app = FastAPI(title="Gym Backend")
    app.include_router(health.router)
    return app


app = create_app()
