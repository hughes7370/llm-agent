"""Implements the application main"""
from common.base import Main
from common.service_management import ServiceManager
from search.manager import SearchServiceManager
from conversation.manager import ConversationServiceManager
from planner.manager import PlannerServiceManager
from LLM.manager import LLMServiceManager
from api_handler.manager import APIHandlerServiceManager
from transformer.manager import TransformerServiceManager
from database.manager import DatabaseServiceManager
from health.manager import HealthServiceManager
from health.controller import HealthRestController
from conversation.controller import ConversationRestController
from conversation.db_models import ConversationModelService

from fastapi import APIRouter

class _ApplicationMainImpl:

    """Implements the application main"""

    def __init__(self, *args, **kwargs):  # pylint: disable=unused-argument
        self._service_manager_2_instance = {}

    def add_service_manager(self, service_manager: ServiceManager):
        """Adds a service manager"""
        self._service_manager_2_instance[service_manager.__class__.__name__] = service_manager

    async def destroy_service_managers(self):
        """Destroy all service managers"""
        for service_manager in self._service_manager_2_instance.values():
            await service_manager.destroy()

    async def prepare_service_managers(self):
        """Prepares all service managers"""
        for service_manager in self._service_manager_2_instance.values():
            await service_manager.prepare()

    async def start_service_managers(self):
        """Starts all service managers"""
        for service_manager in self._service_manager_2_instance.values():
            await service_manager.start()

    async def stop_service_managers(self):
        """Stop all service managers"""
        for service_manager in self._service_manager_2_instance.values():
            await service_manager.stop()

    def service_manager_name(self, service_manager: ServiceManager):
        """Returns the name of the service manager"""
        return service_manager.__class__.__name__

    def service_manager(self, name: str):
        """Returns the service manager"""
        return self._service_manager_2_instance[name]


class ApplicationMain:

    """Implements the main application"""

    _impl = None

    @staticmethod
    async def initialize() -> None:
        """Initializes the Application"""
        await Main.initialize(controller_initializer=ApplicationMain.initialize_controllers)
        ApplicationMain._impl = _ApplicationMainImpl()
        await ApplicationMain.initialize_service_managers()
        await ApplicationMain._impl.prepare_service_managers()
        await ApplicationMain._impl.start_service_managers()

    @staticmethod
    async def initialize_service_managers() -> None:
        """Initializes all service managers"""
        llm_service_manager = LLMServiceManager()
        search_service_manager = SearchServiceManager(llm_service_manager)
        api_handler_service_manager = APIHandlerServiceManager()
        transformer_service_manager = TransformerServiceManager()
        database_service_manager = DatabaseServiceManager()
        planner_service_manager = PlannerServiceManager(llm_service_manager, 
                                                        api_handler_service_manager, 
                                                        search_service_manager, 
                                                        transformer_service_manager, 
                                                        database_service_manager,)
        conversation_service_manager = ConversationServiceManager(
                                            llm_service_manager,
                                            planner_service_manager,
                                            search_service_manager
                                        )
        conversation_model_service_manager =  ConversationModelService(database_service_manager)
        
        ApplicationMain.add_service_manager(search_service_manager)
        ApplicationMain.add_service_manager(conversation_service_manager)
        ApplicationMain.add_service_manager(transformer_service_manager)
        ApplicationMain.add_service_manager(database_service_manager)
        ApplicationMain.add_service_manager(planner_service_manager)
       #ADDED 
        ApplicationMain.add_service_manager(llm_service_manager)
        ApplicationMain.add_service_manager(api_handler_service_manager)

        health_service_manager = HealthServiceManager()
        ApplicationMain.add_service_manager(health_service_manager)
        ApplicationMain.add_service_manager(conversation_model_service_manager)


    @staticmethod
    def initialize_controllers(application: APIRouter) -> None:
        """Initializes all controllers"""
        health_service_manager = ApplicationMain._impl.service_manager(HealthServiceManager.__name__)
        health_rest_controller = HealthRestController(health_service_manager)
        health_rest_controller.prepare(application)
        
        database_service_manager = ApplicationMain._impl.service_manager(DatabaseServiceManager.__name__)
        conversation_model_service_manager = ApplicationMain._impl.service_manager(ConversationModelService.__name__)
        conversation_service_manager = ApplicationMain._impl.service_manager(ConversationServiceManager.__name__)
        conversation_rest_controller = ConversationRestController(conversation_service_manager, conversation_model_service_manager)
        conversation_rest_controller.prepare(application)


    @staticmethod
    async def service_manager(name: str) -> ServiceManager:
        """Returns the service manager"""
        return ApplicationMain._impl.service_manager(name)

    @staticmethod
    async def service_manager_name(service_manager: ServiceManager) -> str:
        """Returns the name of the service manager"""
        return ApplicationMain._impl.service_manager_name(service_manager)

    @staticmethod
    def add_service_manager(service_manager: ServiceManager) -> None:
        """Adds a service manager"""
        ApplicationMain._impl.add_service_manager(service_manager)

    @staticmethod
    async def finalize() -> None:
        """Finalizes the Application"""
        await ApplicationMain._impl.stop_service_managers()
        await ApplicationMain._impl.destroy_service_managers()
        ApplicationMain._impl = None
        await Main.finalize()

    @staticmethod
    def serve() -> None:
        """Serves the application"""
        Main.rest_server().serve()
