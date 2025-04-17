from typing import List, Optional
import chainlit.data as cl_data
from chainlit.step import StepDict, Step
from literalai.helper import utc_now
from chainlit.user import PersistedUser, User, UserDict
from .data_models import Step, StepDict, Thread
from chainlit.session import WebsocketSession
from chainlit.config import config
from chainlit.context import context
import functools
from collections import deque
from .crud import UserCrud, StepCrud, ThreadCrud
import json
from common.base import Main
import aiofiles
now = utc_now()

from common.utils import send_alert
import datetime


thread_history = [
    {
        "id": "b8e20ac4-e03a-4bbb-8006-338d18020b77",
        "name": "thread 1",
        "createdAt": now,
        "userId": "test",
        "userIdentifier": "admin",
        "steps": [ 
            {
                "id": "test1",
                "name": "test",
                "createdAt": now,
                "type": "user_message",
                "output": "Message 1",
            },
            {
                "id": "test2",
                "name": "test",
                "createdAt": now,
                "type": "assistant_message",
                "output": "Message 2",
            },
        ], 
    },
    {
        "id": "test2",
        "createdAt": now,
        "userId": "test",
        "userIdentifier": "admin",
        "name": "thread 2",
        "steps": [
            {
                "id": "test3",
                "createdAt": now,
                "name": "test",
                "type": "user_message",
                "output": "Message 3",
            },
            {
                "id": "test4",
                "createdAt": now,
                "name": "test",
                "type": "assistant_message",
                "output": "Message 4",
            },
        ],
    },
]  # type: List[cl_data.ThreadDict]
# deleted_thread_ids = []  # type: List[str]


def queue_until_user_message():
    def decorator(method):
        @functools.wraps(method)
        async def wrapper(self, *args, **kwargs):
            if (
                isinstance(context.session, WebsocketSession)
                and not context.session.has_first_interaction
            ):
                # Queue the method invocation waiting for the first user message
                queues = context.session.thread_queues
                method_name = method.__name__
                if method_name not in queues:
                    queues[method_name] = deque()
                queues[method_name].append((method, self, args, kwargs))

            else:
                # Otherwise, Execute the method immediately
                return await method(self, *args, **kwargs)

        return wrapper
    return decorator


class CustomDataLayer(cl_data.BaseDataLayer):

    def __init__(self):
        self.user = UserCrud()
        self.step = StepCrud()
        self.thread = ThreadCrud()
        Main.logger().info("Chainlit data layer initialized")

    async def get_user(self, identifier: str) -> Optional[PersistedUser]:
            try:
                # Main.logger().info("Gettingg...")
                user =self.user.get_user(identifier=identifier)
                # Main.logger().info(f'User is {user}')
                # Main.logger().info(f'Getting persisted user {user.identifier} {user.id}, {user.metadata_}, {user.createdAt}')
                if not user:
                    # Main.logger().info("Got none while getting user")
                    return None
                
                user =  PersistedUser(
                    id=user.id or "",
                    identifier=user.identifier or "",
                    metadata=user.metadata_,
                    createdAt=user.createdAt.strftime("%Y-%m-%d") or "",
                )

                # Main.logger().info(f'Getting persisted user {user.identifier} {user.id}, {user.metadata}, {user.createdAt}')
                return user
            except BaseException as e:
                error_msg = f"Something went wrong while getting user {identifier} with {e}"
                Main.logger().debug(error_msg, exc_info=1)
                send_alert(
                    message=f"<b>The following issues have occured </b> \n <pre> {error_msg} </pre> </b> <b> - As a fix, you can try restarting the container </b>",
                    subject=f'Error on  server chainlit telemetry on {datetime.utcnow().strftime("%a %b %d %H:%M:%S UTC %Y")}',
                )

    async def create_user(self, user: User) -> Optional[PersistedUser]:
        try:
            _user = self.user.create_user(identifier=user.identifier, metadata=user.metadata)

            if not _user:
                _user = self.user.create_user(
                    identifier=user.identifier, metadata=user.metadata
                )
            elif _user.id:
                self.user.update_user(id=_user.id, metadata=user.metadata)

            user =  PersistedUser(
                id=_user.id or "",
                identifier=_user.identifier or "",
                metadata=_user.metadata_,
                createdAt=str(_user.createdAt) or "",
            )
            # Main.logger().info(f'Getting persisted user from create {user.identifier} {user.id}, {user.metadata}, {user.createdAt}')
            return user
        except BaseException as e:
            error_msg = f"Something went wrong while creating user {user} with {e}"
            Main.logger().debug(error_msg, exc_info=1)
            send_alert(
                message=f"<b>The following issues have occured </b> \n <pre> {error_msg} </pre> </b> <b> - As a fix, you can try restarting the container </b>",
                subject=f'Error on  server chainlit telemetry on {datetime.utcnow().strftime("%a %b %d %H:%M:%S UTC %Y")}',
            )

    @queue_until_user_message()
    async def create_step(self, step_dict: "StepDict"):
        try:
            # Main.logger().info(f"Creating steps from crud : {step_dict.keys()}")
            metadata = dict(
                step_dict.get("metadata", {}),
                **{
                    "disableFeedback": step_dict.get("disableFeedback"),
                    "isError": step_dict.get("isError"),
                    "waitForAnswer": step_dict.get("waitForAnswer"),
                    "language": step_dict.get("language"),
                    "showInput": step_dict.get("showInput"),
                },
            )

            step = {
                "createdAt": step_dict.get("createdAt"), 
                "start": step_dict.get("start"), 
                "end": step_dict.get("end"),
                "generation": step_dict.get("generation"),
                "id": step_dict.get("id"),
                "parentId": step_dict.get("parentId"),
                "name": step_dict.get("name"),
                "threadId": step_dict.get("threadId"),
                "type": step_dict.get("type"),
                "tags": step_dict.get("tags"),
                "metadata": metadata,
            }
            if step_dict.get("input"):
                step["input"] = {"content": step_dict.get("input")}
                # step["input"] = step_dict.get("input")
            if step_dict.get("output"):
                step["output"] = {"content": step_dict.get("output")}
                # step["output"] = step_dict.get("output")

            self.step.create_step(step)
        except BaseException as e:
            error_msg = f"Something went wrong while creating step {step} with {e}"
            Main.logger().debug(error_msg, exc_info=1)
            send_alert(
                message=f"<b>The following issues have occured </b> \n <pre> {error_msg} </pre> </b> <b> - As a fix, you can try restarting the container </b>",
                subject=f'Error on  server chainlit telemetry on {datetime.utcnow().strftime("%a %b %d %H:%M:%S UTC %Y")}',
            )


    @queue_until_user_message()
    async def update_step(self, step_dict: "StepDict"):
        # Main.logger().info("Updating step from crud")
        try:
            await self.create_step(step_dict)
        except BaseException as e:
            error_msg = f"Something went wrong while updating step {step_dict} with {e}"
            Main.logger().debug(error_msg, exc_info=1)
            send_alert(
                message=f"<b>The following issues have occured </b> \n <pre> {error_msg} </pre> </b> <b> - As a fix, you can try restarting the container </b>",
                subject=f'Error on  server chainlit telemetry on {datetime.utcnow().strftime("%a %b %d %H:%M:%S UTC %Y")}',
            )


    @queue_until_user_message()
    async def delete_step(self, step_id: str):
        try:
            self.step.delete_step(step_id=step_id)
        except BaseException as e:
            error_msg = f"Something went wrong while deleting step {step_id} with {e}"
            Main.logger().debug(error_msg, exc_info=1)
            send_alert(
                message=f"<b>The following issues have occured </b> \n <pre> {error_msg} </pre> </b> <b> - As a fix, you can try restarting the container </b>",
                subject=f'Error on  server chainlit telemetry on {datetime.utcnow().strftime("%a %b %d %H:%M:%S UTC %Y")}',
            )

    def step_to_step_dict(self, step: Step) -> "StepDict":
        # metadata = step.metadata or {}
        input = (step.input or {}).get("content") or (
            json.dumps(step.input) if step.input and step.input != {} else ""
        )
        output = (step.output or {}).get("content") or (
            json.dumps(step.output) if step.output and step.output != {} else ""
        )

        # user_feedback = (
        #     next(
        #         (
        #             s
        #             for s in step.scores
        #             if s.type == "HUMAN" and s.name == "user-feedback"
        #         ),
        #         None,
        #     )
        #     if step.scores
        #     else None
        # )

        return {
            "createdAt": step.createdAt,
            "id": step.id or "",
            "threadId": step.threadId or "",
            "parentId": step.parentId,
            # "feedback": self.score_to_feedback_dict(user_feedback),
            "start": step.start,
            "end": step.end,
            "type": step.type or "undefined",
            "name": step.name or "",
            "generation": step.generation.to_dict() if step.generation else None,
            "input": input,
            "output": output,
            # "showInput": metadata.get("showInput", False),
            # "disableFeedback": metadata.get("disableFeedback", False),
            # "indent": metadata.get("indent"),
            # "language": metadata.get("language"),
            # "isError": metadata.get("isError", False),
            # "waitForAnswer": metadata.get("waitForAnswer", False),
        }

    def attachment_to_element_dict(self, attachment) :
        metadata = attachment.metadata or {}
        return {
            "chainlitKey": None,
            "display": metadata.get("display", "side"),
            "language": metadata.get("language"),
            "page": metadata.get("page"),
            "size": metadata.get("size"),
            "type": metadata.get("type", "file"),
            "forId": attachment.step_id,
            "id": attachment.id or "",
            "mime": attachment.mime,
            "name": attachment.name or "",
            "objectKey": attachment.object_key,
            "url": attachment.url,
            "threadId": attachment.thread_id,
        }

    async def get_element(
        self, thread_id: str, element_id: str
    ):
        # attachment = await self.client.api.get_attachment(id=element_id)
        attachment = None
        if not attachment:
            return None
        return self.attachment_to_element_dict(attachment)

    @queue_until_user_message()
    async def create_element(self, element):
        metadata = {
            "size": element.size,
            "language": element.language,
            "display": element.display,
            "type": element.type,
            "page": getattr(element, "page", None),
        }

        if not element.for_id:
            return

        object_key = None

        if not element.url:
            if element.path:
                async with aiofiles.open(element.path, "rb") as f:
                    content = await f.read() 
            elif element.content:
                content = element.content
                # Main.logger().info(f"Element content: {content}")
            else:
                raise ValueError("Either path or content must be provided")
            # uploaded = await self.client.api.upload_file(
            #     content=content, mime=element.mime, thread_id=element.thread_id
            # )
            # object_key = uploaded["object_key"]

        await self.create_step(
            
                {
                    "id": element.for_id,
                    "threadId": element.thread_id,
                    "output" : content,
                    "attachments": [
                        {
                            "id": element.id,
                            "name": element.name,
                            "metadata": metadata,
                            "mime": element.mime,
                            "url": element.url,
                            # "objectKey": object_key,
                        }
                    ],
                }
            
        )

    async def get_thread_author(self, thread_id: str) -> str:
        try:
            # Main.logger().info(f"Getting thread author for {thread_id}")
            thread = self.thread.read_thread(thread_id)
            if not thread:
                # Main.logger().info(f"No thread found")
                return ""
            # user_identifier = thread.participantIdentifier
            user_identifier = self.user.get_user_by_id(userId=thread.participantId).identifier
            if not user_identifier:
                # Main.logger().info(f"No user in thread found")
                return ""

            # Main.logger().info(f"User in thread found {user_identifier}")
            return user_identifier
        except BaseException as e:
            error_msg = f"Something went wrong while getting author for thread {thread_id} with {e}"
            Main.logger().debug(error_msg, exc_info=1)
            send_alert(
                message=f"<b>The following issues have occured </b> \n <pre> {error_msg} </pre> </b> <b> - As a fix, you can try restarting the container </b>",
                subject=f'Error on  server chainlit telemetry on {datetime.utcnow().strftime("%a %b %d %H:%M:%S UTC %Y")}',
            )

    async def get_thread(self, thread_id: str) :
        try:
            thread = self.thread.read_thread(thread_id=thread_id)
            if not thread:
                return None
            elements = []  # List[ElementDict]
            steps = []  # List[StepDict]
            if thread:
                db_steps = self.step.get_steps_per_thread(thread_id=thread_id)
                for step in db_steps:
                    if config.ui.hide_cot and step.parentId:
                        continue
                    # for attachment in step.attachments:
                    #     elements.append(self.attachment_to_element_dict(attachment))
                    if not config.features.prompt_playground and step.generation:
                        step.generation = None
                    steps.append(self.step_to_step_dict(step))

            # Main.logger().info(f"Getting the selected thread {thread}")
            return {
                "createdAt": thread.createdAt or "",
                "id": thread.id,
                "name": thread.name or None,
                "steps": steps,
                "elements": elements,
                "metadata": thread.metadata_,
                "userId": thread.participantId,
                "userIdentifier": thread.participantIdentifier,
                "tags": thread.tags,
            }
        except BaseException as e:
            error_msg = f"Something went wrong while getting thread {thread_id}"
            Main.logger().debug(error_msg, exc_info=1)
            send_alert(
                message=f"<b>The following issues have occured </b> \n <pre> {error_msg} </pre> </b> <b> - As a fix, you can try restarting the container </b>",
                subject=f'Error on  server chainlit telemetry on {datetime.utcnow().strftime("%a %b %d %H:%M:%S UTC %Y")}',
            )

    async def update_thread(
        self,
        thread_id: str,
        name: Optional[str] = None,
        user_id: Optional[str] = None,
        metadata: Optional[dict] = None,
        tags: Optional[List[str]] = None,
    ):
        try:
            # Main.logger().info(f"Upseting thread with {thread_id}, {name}, {user_id}, {metadata}, {tags}.")
            thread = self.thread.upsert_thread(
                id=thread_id,
                name=name,
                participant_id=user_id,
                metadata=metadata,
                tags=tags,
            )
            # Main.logger().info(f"Upsetted thread with {thread.id}, {thread.name}, {thread.participantId}, {thread.tags}.")
        except BaseException as e:
            error_msg = f"Something went wrong while updating thread {thread_id} with {e}"
            Main.logger().debug(error_msg, exc_info=1)
            send_alert(
                message=f"<b>The following issues have occured </b> \n <pre> {error_msg} </pre> </b> <b> - As a fix, you can try restarting the container </b>",
                subject=f'Error on  server chainlit telemetry on {datetime.utcnow().strftime("%a %b %d %H:%M:%S UTC %Y")}',
            )

    async def delete_thread(self, thread_id: str):
        try:
            self.thread.delete_thread(thread_id=thread_id)
        except BaseException as e:
            error_msg  = f"Something went wrong while deleting thread {thread_id} with {e}"
            Main.logger().debug(error_msg, exc_info=1)
            send_alert(
                message=f"<b>The following issues have occured </b> \n <pre> {error_msg} </pre> </b> <b> - As a fix, you can try restarting the container </b>",
                subject=f'Error on  server chainlit telemetry on {datetime.utcnow().strftime("%a %b %d %H:%M:%S UTC %Y")}',
            )

    async def list_threads(
        self, pagination: cl_data.Pagination, filter: cl_data.ThreadFilter
    ) -> cl_data.PaginatedResponse[cl_data.ThreadDict]:
        thread_historyy = self.thread.thread_history(userId=filter.userId)
        # Main.logger().info(f"Thread history filters: {filter.userId}")
        # Main.logger().info(f"Thread history feedback: {filter.feedback}")
        # Main.logger().info(f"Thread history feedback: {filter.search}")
        
        try:
            return cl_data.PaginatedResponse(
                data=[t for t in thread_historyy],
                pageInfo=cl_data.PageInfo(
                    hasNextPage=False, startCursor=None, endCursor=None
                ),
            )
        except BaseException as e:
            error_msg = f"Something went wrong while listing threads for {filter} with {e}"
            Main.logger().debug(error_msg, exc_info=1)
            send_alert(
                message=f"<b>The following issues have occured </b> \n <pre> {error_msg} </pre> </b> <b> - As a fix, you can try restarting the container </b>",
                subject=f'Error on  server chainlit telemetry on {datetime.utcnow().strftime("%a %b %d %H:%M:%S UTC %Y")}',
            )
    
    async def delete_feedback(
        self,
        feedback_id: str,
    ):
        if feedback_id:
            self.step.delete_step(
                step_id=feedback_id,
            )
            return True
        return False

    async def upsert_feedback(
        self,
        feedback,
    ):
        try:
            if feedback.id:
                self.step.upsert_score(
                    step_id=feedback.forId,
                    value=feedback.value,
                    comment=feedback.comment,
                    name="user-feedback",
                    type="HUMAN",
                )
                return feedback.id
            else:
                created = self.step.upsert_score(
                    step_id=feedback.forId,
                    value=feedback.value,
                    comment=feedback.comment,
                    name="user-feedback",
                    type="HUMAN",
                )
                return  ""
        except BaseException as e:
            error_msg = f"Something went wrong while updating feedback {feedback} with {e}"
            Main.logger().debug(error_msg, exc_info=1)
            send_alert(
                message=f"<b>The following issues have occured </b> \n <pre> {error_msg} </pre> </b> <b> - As a fix, you can try restarting the container </b>",
                subject=f'Error on  server chainlit telemetry on {datetime.utcnow().strftime("%a %b %d %H:%M:%S UTC %Y")}',
            )
        