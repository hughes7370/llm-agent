"""Defines Service and ServiceManager"""


class Service:

    """Implements a base service"""

    async def prepare(self):
        """Prepares the service"""

    async def start(self):
        """Starts the service"""

    async def stop(self):
        """Stops the service"""

    async def validate(self):
        """Validates the service"""


class ServiceManager:

    """Implements a base service manager"""

    async def destroy(self):
        """Destroys the service manager"""

    async def prepare(self):
        """Prepares the service manager"""

    async def start(self):
        """Starts the service manager"""

    async def stop(self):
        """Stops the service manager"""

    async def validate(self):  # pylint: disable=no-self-use
        """Validates the service manager"""
        return []
