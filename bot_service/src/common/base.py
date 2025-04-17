"""Implements the logger"""

from common.configuration import Configuration
from common.storage.storage import StorageService
from common.data_model import StorageConfiguration
from collections import OrderedDict
import logging.handlers
import logging
from typing import Callable


import uvicorn
from common.data_model import ServerConfiguration
from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware


DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
LOGGER_FORMAT = "%(asctime)s.%(msecs)03d|%(name)s|%(funcName)s|%(levelname)s|%(message)s"
logging.basicConfig(format=LOGGER_FORMAT, datefmt=DATE_FORMAT)


class Logger:

    """Defines a logger for an application"""

    LOG_FILE_MAX_BYTES = 10 * 1024 * 1024
    LOG_FILE_BACKUP_COUNT = 5
    VALID_LOG_LEVELS = OrderedDict(
        sorted({x: logging._levelToName[x] for x in logging._levelToName  # pylint: disable=protected-access
                if str(x).isdigit()}.items()))

    def __init__(self, application_name, logger_configuration):
        log_level = logger_configuration.log_level
        self._application_name = application_name
        self._logger = logging.getLogger(self._application_name)
        self.set_properties(log_level)

    def set_properties(self, level):
        """Sets the logger properties"""
        if level is None:
            level = logging.WARNING
        self._logger.setLevel(level)

    def logger(self):
        """Returns the logger instance"""
        return self._logger

class RestServer:
    """Defines the REST server"""

    def __init__(self, server_configuration: ServerConfiguration, controller_initializer: Callable[[APIRouter], None]):
        self._application = FastAPI(docs_url="/documentation", redoc_url="/redocumentation")
        self._api_router = APIRouter(prefix="/api")
        self._application.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        self._controller_initializer = controller_initializer
        self._server_configuration = server_configuration

    def serve(self) -> None:
        """Serves the REST server"""
        self._controller_initializer(self._api_router)
        self._application.include_router(self._api_router)
        uvicorn.run(
            self._application, host=self._server_configuration.host, port=int(self._server_configuration.port))

    def application(self) -> FastAPI:
        """Returns the application instance"""
        return self._application

class _MainImpl:

    """Stores the internal data members accessible via the 'Main' class"""

    def __init__(self, *args, **kwargs):  # pylint: disable=unused-argument
        self._configuration = Configuration()
        configuration_model = self._configuration.configuration()
        self._application_name = configuration_model.application_name
        self._logger = Logger(
            self._application_name, configuration_model.logger_configuration)
        server_configuration = configuration_model.server_configuration
        controller_initializer = kwargs.get("controller_initializer")
        self._rest_server = RestServer(
            server_configuration=server_configuration, controller_initializer=controller_initializer)
        
        self._storage = StorageService(StorageConfiguration().storage_type)

    def application_name(self):
        """Returns the application name"""
        return self._application_name

    def configuration(self):
        """Returns the configuration"""
        return self._configuration

    def logger(self):
        """Returns the logger"""
        return self._logger
    
    def rest_server(self):
        """Returns the REST server"""
        return self._rest_server
    
    def storage(self):
        """Returns the Storage server"""
        return self._storage


class Main:
    """Defines the scaffolding Main class"""

    _impl = None

    @staticmethod
    def _assert_initialized():
        """Asserts that 'Main' is initialized"""
        assert Main._impl is not None, "'Main' has not been initialized yet"

    @staticmethod
    def application_name():
        """Returns the application name"""
        Main._assert_initialized()
        return Main._impl.application_name()

    @staticmethod
    def configuration():
        """Returns the configuration object instance"""
        Main._assert_initialized()
        return Main._impl.configuration().configuration()

    @staticmethod
    def finalize(*args, **kwargs):  # pylint: disable=unused-argument
        """Finalizes all global singletons in this scope"""
        Main._assert_initialized()
        Main._impl = None

    @staticmethod
    async def initialize(*args, **kwargs):
        """Initializes all global singletons in this scope"""
        assert Main._impl is None, "'Main' has already been initialized"
        Main._impl = _MainImpl(*args, **kwargs)

    @staticmethod
    def initialized():
        """Returns True if 'Main' has been initialized"""
        return Main._impl is not None

    @staticmethod
    def logger():
        """Returns logger object instance"""
        Main._assert_initialized()
        return Main._impl.logger().logger()

    @staticmethod
    def rest_server():
        """Returns the REST server"""
        Main._assert_initialized()
        return Main._impl.rest_server()
    
    @staticmethod
    def storage():
        """Returns the REST server"""
        Main._assert_initialized()
        return Main._impl.storage()