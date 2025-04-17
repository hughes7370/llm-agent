from common.service_management import ServiceManager
from common.base import Main
from health.model import HealthResponse


class HealthServiceManager(ServiceManager):
    """Implements the health service manager"""

    async def ping(self) -> HealthResponse:
        """Returns the health response"""
        Main.logger().info("HealthServiceManager.ping")
        return HealthResponse(alive=True)
