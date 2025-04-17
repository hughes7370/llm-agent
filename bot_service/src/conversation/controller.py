"""Conversation REST controller module"""
from common.controller import RestController
from common.base import Main
from common.data_model import QueryContext, Roles
from conversation.manager import ConversationServiceManager
from conversation.db_models import ConversationModelService

from conversation.model import  ConversationResponse, ConversationRequest
from fastapi import APIRouter, Depends, status, HTTPException
from fastapi.security import HTTPBasicCredentials, HTTPBasic
from typing import Annotated
import secrets
from time import perf_counter
import json

from langchain.memory import ConversationBufferWindowMemory
from langchain_core.messages.human import HumanMessage
from langchain_core.messages.ai import AIMessage

from psycopg2.errors import OperationalError as PsycopgOperationalError
from sqlalchemy.exc import OperationalError as SQLAlchemyOperationalError

async def dummy_stream_response(msg: str):
    pass

security = HTTPBasic()

class ConversationRestController(RestController):
    """Implements Conversation REST controller"""

    def __init__(self, conversation_service_manager: ConversationServiceManager, conversation_model_service :ConversationModelService) -> None:
        super().__init__()
        self._conversation_service_manager = conversation_service_manager
        self.conversation_db_model_service = conversation_model_service
    
    def get_current_username(self,credentials: Annotated[HTTPBasicCredentials, Depends(security)]):
        
        current_username_bytes = credentials.username.encode("utf8")
        current_password_bytes = credentials.password.encode("utf8")
        
        oauth_file_path = Main.configuration().user_configuration.user_directory
        with open(oauth_file_path, 'r') as f:
            users_credentials = json.load(f)
        
        is_correct_username, is_correct_password = False, False

        for user_credential in users_credentials:
            correct_username_bytes = bytes(str(user_credential.get('username')), encoding='utf8')
            correct_password_bytes = bytes(str(user_credential.get('password')), encoding='utf8')
            
            is_correct_username = secrets.compare_digest(current_username_bytes, correct_username_bytes)
            is_correct_password = secrets.compare_digest(current_password_bytes, correct_password_bytes)

            if not (is_correct_username and is_correct_password):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Incorrect username or password",
                    headers={"WWW-Authenticate": "Basic"},
                )
            
            return credentials.username

    def get_conversation_msgs(self,raw_converstion_context: dict):
        
        converstion_context = json.loads(raw_converstion_context)
        conversation_msgs = []

        for msg in converstion_context.get('queries'):
            conversation_msgs.append(HumanMessage(msg[0]))
            conversation_msgs.append(AIMessage(msg[1]))
        
        return conversation_msgs
    
    @staticmethod
    def get_conversation_base():
        return Main.storage().get_base()

    def prepare(self, app: APIRouter) -> None:
        """Prepares the service"""

        # postgres_db_service = self.database_manager.postgres_db_service()
        # # Create the base tables
        # db_models.Base.metadata.create_all(bind=postgres_db_service.engine)

        @app.post("/converse", response_model=ConversationResponse, status_code=status.HTTP_200_OK, tags=["converse"])
        async def converse(username: Annotated[str, Depends(self.get_current_username)], converse_request: ConversationRequest = Depends()):
            try:
                """Returns the converse response"""
                conversation_context = ConversationBufferWindowMemory(k=10)
                db_thread = -1
                
                if converse_request.context_id:
                    try:
                        db_thread = self.conversation_db_model_service.get_converse_thread(db=self.conversation_db_model_service.database_manager.postgres_db_service().get_db_session(),thread_id=converse_request.context_id) 
                        if db_thread:
                            conversation_msgs = self.get_conversation_msgs(db_thread.context)
                            conversation_context.chat_memory.add_messages(conversation_msgs)
                            Main.logger().info(f"Thread id {converse_request.context_id} updated with context for user {username} : {conversation_context.buffer_as_messages}")
                    
                    except (PsycopgOperationalError, SQLAlchemyOperationalError ) as e:
                        Main.logger().critical(f"Retrieving the context for context id {converse_request.context_id} from db failed due to ..{e}, context will not work !")

                Main.logger().critical(f"Conv req : {converse_request}")
                query_context = QueryContext(
                    query=converse_request.query,
                    role=converse_request.user_role.value,
                    stream_response=lambda response: dummy_stream_response(converse_request.query),
                    conversation_context=conversation_context
                )

                step_functions = {
                    "planner":dummy_stream_response,
                    "api":dummy_stream_response,
                    "aggregation":dummy_stream_response,
                    "summerization":dummy_stream_response,
                    "clarification":dummy_stream_response,
                    "search":dummy_stream_response
                }
                
                start_time = perf_counter()
                converse_response =  await self._conversation_service_manager.converse_api(query_context, step_functions, planner=converse_request.planner.value)
                end_time = perf_counter()
                
                Main.logger().info(f"The conversation response for thread id {converse_request.context_id} & user {username} : {converse_response}")

                try:
                    db_thread = self.conversation_db_model_service.upsert_converse_thread(
                        db=self.conversation_db_model_service.database_manager.postgres_db_service().get_db_session(),
                        thread_id=converse_request.context_id,
                        thread_context=(converse_request.query, converse_response),
                        username=username,
                    )
                except (PsycopgOperationalError, SQLAlchemyOperationalError, AttributeError) as e:
                    Main.logger().critical(f"Saving the thread to db failed due to ..{e}, cannot generate thread id !")

                return ConversationResponse(
                    response=converse_response,
                    context_id=db_thread,
                    response_time_in_seconds=f"{end_time - start_time:.4}"
                )
            
            except BaseException as e:
                Main.logger().error(f"Failed while conversing with error .. {e}", exc_info=1)
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed while conversing with error .. {e}")