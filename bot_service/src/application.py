import chainlit as cl
from chainlit.input_widget import Select, Switch, Slider
from chainlit import config
from main import ApplicationMain
from conversation.manager import ConversationServiceManager
from common.base import Main
from common.data_model import Roles
from api_handler.manager import APIHandlerServiceManager
from typing import Any
from common.data_model import QueryContext
import json
from langchain.memory import ConversationBufferWindowMemory
from chainlit_data_pers.chainlit_data import CustomDataLayer
import chainlit.data as cl_data
import uuid


# Initializing services and session


# # TODO: Have a relational db service to enable thread history
# try:
#     cl_data._data_layer = CustomDataLayer()
# except BaseException as e: 
#     Main.logger().critical("Skipping thread history ..")

@cl.on_chat_start
async def start():
    # clear the context on new chat
    query_context = cl.user_session.get("query_context")
    if query_context:
        query_context.conversation_context.clear()
        cl.user_session.set("query_context", query_context)
        Main.logger().critical("Chat context cleared !")

    await cl.ChatSettings(
        [Switch(id="VERBOSE", label="Enable verbose mode", initial=False, tooltip="Make the output more verbose"),
         Switch(id="RUN_TEST", label="Enable test execution", initial=False, tooltip="Generate the prompt/response pairs"),
         Select(
                id="ROLE",
                label="Select Your Role",
                # values=["Admin", "Passenger", "Logistics","Developer"], # Replace the values with actual roles
                values=Roles.list(), # Replace the values with actual roles
                initial_index=0, # 0-based index, it will select the first role( Admin ) as default,
                tooltip="Select the persona type"
            ),
         ]).send()
    cl.user_session.set("RUN_TEST", False)
    cl.user_session.set("VERBOSE", False)

    logged_in_user_role = cl.user_session.get('user').metadata.get('ROLE')
    cl.user_session.set("ROLE", logged_in_user_role)

    cl.user_session.set("context", ConversationBufferWindowMemory(k=10))
    conversation_service_manager = await ApplicationMain.service_manager(ConversationServiceManager.__name__)
    # api_handler_service_manager = await ApplicationMain.service_manager(APIHandlerServiceManager.__name__)
    Main.logger().info("Initialized Chainlit Application")
    cl.user_session.set("conversation_service_manager",
                        conversation_service_manager)
    
    await cl.Avatar(
        name="API AI agent",
        path="./store/avatars/IMG_5801.JPG", size="medium"
    ).send()

    await cl.Avatar(
        name="User",
        path="./store/avatars/IMG_5799.JPG", size="medium"
    ).send()


@cl.step(name="AI agents", type="assistant_message")
async def create_chat_step(input):
    return input

@cl.step(name="Planner Agent", type="assistant_message")
async def create_planner_step(input):
    return input

@cl.step(name="API Agent", type="assistant_message")
async def create_api_step(input):
    return input

@cl.step(name="Data Analyst Agent", type="assistant_message")
async def create_aggregation_step(input):
    return input

@cl.step(name="Summarization Agent", type="assistant_message")
async def create_summerizartion_step(input):
    return input

@cl.step(name="Clarification", type="assistant_message")
async def create_clarification_step(input):
    return input

@cl.step(name="Internet Search Agent", type="assistant_message")
async def create_search_step(input):
    return input

step_functions = {
    "planner":create_planner_step,
    "api":create_api_step,
    "aggregation":create_aggregation_step,
    "summerization":create_summerizartion_step,
    "search": create_search_step,
    "clarification":create_clarification_step
}


@cl.password_auth_callback
def auth_callback(username: str, password: str):
    # Verify username and password against the user database in the JSON file
    Main.logger().info(f"Checking credentials from {Main.configuration().user_configuration.user_directory}")
    oauth_file_path = Main.configuration().user_configuration.user_directory
    with open(oauth_file_path, 'r') as f:
        users_credentials = json.load(f)
    
    # Assuming the JSON file contains a list of user credentials
    for user_credential in users_credentials:
        if (username, password) == (user_credential.get('username'), user_credential.get('password')):
            role = user_credential.get("role")
            return cl.User(identifier=username, metadata={"ROLE": role, "provider": "credentials"})
    
    # If no match was found, return None
    return None

@cl.on_settings_update
async def setup_agent(settings):
    print("on_settings_update", settings)
    cl.user_session.set("VERBOSE",settings.get("VERBOSE"))
    cl.user_session.set("RUN_TEST",settings.get("RUN_TEST"))
    cl.user_session.set("ROLE", settings.get("ROLE"))


@cl.action_callback("Clear context")
async def on_action(action):
    query_context = cl.user_session.get("query_context")
    query_context.conversation_context.clear()
    cl.user_session.set("query_context", query_context)
    Main.logger().info("Chat context cleared !")

async def stream_response(msg: Any, response: Any) -> None:
    """Streams the response to the user"""
    if cl.user_session.get("VERBOSE"):
        await msg.stream_token(str(response))


@cl.on_message
async def main(message: str):
    """On Message handler"""
    conversation_service_manager = cl.user_session.get(
        "conversation_service_manager")
    cl.Message(author="User", content=message)
    role = cl.user_session.get("ROLE")

    if (cl.user_session.get("RUN_TEST")):
        role = Roles.Developer.value
        query_file_name = Main.configuration().common_configuration.llm_pr_queries_file # "list_of_test_queries.json"
        with open(query_file_name, "r") as file:
            list_of_queries_dict = json.load(file)
            list_of_queries = list_of_queries_dict.get("queries")

            for query in list_of_queries:
                Main.logger().info(f"Message Received from user: {message.content}")
                msg = cl.Message(
                    content="Running test mode..", language="markdown")
                id = await msg.send()
                query_context = QueryContext(
                    query=query, role=role, stream_response=lambda response: stream_response(msg, response))
                query_context.conversation_context = cl.user_session.get("context")
                conv_response = await conversation_service_manager.converse(query_context)
                id = await msg.send()
        await cl.Message(content=str("Running test mode finished.."), language="markdown").send()

    else:
        role = cl.user_session.get("ROLE")
        logged_in_user = cl.user_session.get("user")
        
        # logged_in_user.identifier
        Main.logger().info(f"Message received from user : {logged_in_user.identifier} as {role} : {message.content}")

        msg = cl.Message(content="")
        id = await msg.send()
        await create_chat_step("I've received your message and will shortly come up with a plan",)

        query_context = QueryContext(
            query=message.content, role=role, stream_response=lambda response: stream_response(msg, response))
        
        empty_query_context = query_context.copy()

        cl.user_session.set("query_context", query_context)
        query_context.conversation_context = cl.user_session.get("context")
        
        conv_response = await conversation_service_manager.converse(query_context, step_functions)
        
        actions = [cl.Action(name="Clear context",value="" ,label="Clear context")]

        await cl.Message(content="Final Response",elements=[cl.Text(name="", content=str(conv_response), display="inline")],actions=actions).send()

