"""Health REST controller module"""
from common.controller import RestController
from health.manager import HealthServiceManager
from health.model import HealthResponse
from fastapi import APIRouter


class HealthRestController(RestController):
    """Implements health REST controller"""

    def __init__(self, health_service_manager: HealthServiceManager) -> None:
        super().__init__()
        self._health_service_manager = health_service_manager

    def prepare(self, app: APIRouter) -> None:
        """Prepares the service"""

        @app.get("/health", response_model=HealthResponse)
        async def health() -> HealthResponse:
            """Returns the health response"""
            return await self._health_service_manager.ping()
