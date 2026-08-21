from fastapi import FastAPI

from app.routers import admin_auth, health


def create_app() -> FastAPI:
    app = FastAPI(title="Gym Backend")
    app.include_router(health.router)
    app.include_router(admin_auth.router)
    return app


app = create_app()
