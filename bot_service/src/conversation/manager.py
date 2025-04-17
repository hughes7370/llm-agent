from common.service_management import ServiceManager
from search.manager import SearchServiceManager
from common.base import Main
from common.utils import timeit
from planner.manager import PlannerServiceManager
from LLM.manager import LLMServiceManager
from langchain.memory import ConversationBufferWindowMemory
from common.data_model import QueryContext


class ConversationServiceManager(ServiceManager):

    def __init__(self, llm_service_manager: LLMServiceManager, planner_service_manager: PlannerServiceManager, search_service_manager: SearchServiceManager):
        self._search_service_manager = search_service_manager
        self._planner_service_manager = planner_service_manager
        self._llm_service_manager = llm_service_manager
        self._context = ConversationBufferWindowMemory(k=10)

    @timeit
    async def converse(self, query_context: QueryContext, create_step) -> str:
        """Converses with the user"""
        query = query_context.query
        stream_response = query_context.stream_response
        role = query_context.role
        Main.logger().info(f"Query Context {query_context}")
        planner_response = await self._planner_service_manager.planner(query_context, role=role)
        Main.logger().info(f"\n\n Planner Response is {planner_response}")
        if planner_response:
            # self._context.save_context({"inputs": query}, {"outputs": planner_response})
            query_context.conversation_context.save_context({"inputs": query}, {"outputs": planner_response})
        # Main.logger().info(f"Saved context after planner response is {self._context.load_memory_variables({})}")
        awaitable_response = await self._planner_service_manager.execute_tasks(planner_response, query_context, create_step)
        return awaitable_response
        
        # await cl.Message(content=f"Generated final response: \n{response}",).send()

    async def converse_api(self, query_context: QueryContext, create_step, planner: str = "planner_withAPIs") -> str:
        """Converses with the user"""
        query = query_context.query
        stream_response = query_context.stream_response
        role = query_context.role
        # query_context.conversation_context = self._context
        Main.logger().info(f"Query Context {query_context}")
        # planner_response = await self._planner_service_manager.planner2(query)
        # direct_response = await self._search_service_manager.search(query)
        # self._context.save_context(query)
        # Main.logger().info(f"Saved context is {self._context.load_memory_variables({})}")
        planner_response = await self._planner_service_manager.planner(query_context, role=role, planner_name=planner)
        Main.logger().info(f"Planner Response is : {planner_response}")

        # await stream_response(f"Generated thought process: \n{planner_response}")
        if planner_response:
            # self._context.save_context({"inputs": query}, {"outputs": planner_response})
            query_context.conversation_context.save_context({"inputs": query}, {"outputs": planner_response})
        # Main.logger().info(f"Saved context after planner response is {self._context.load_memory_variables({})}")
        awaitable_response = await self._planner_service_manager.execute_tasks(planner_response, query_context, create_step)
        return awaitable_response