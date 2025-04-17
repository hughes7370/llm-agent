from .data_models import User, Step, Thread, database_manageer
from sqlalchemy.orm import Session
from sqlalchemy import  JSON, Integer
from sqlalchemy.sql.expression import cast
import uuid
from common.base import Main

class UserCrud():
    def __init__(self) -> None:
        self.session: Session = database_manageer.postgres_db_service().get_db_session()

    def create_user(self, identifier: str, metadata: dict):
        # Main.logger().info(f"Creating user with {identifier}")
        user = User(
            id=str(uuid.uuid4()),
            identifier = identifier,
            metadata_ = metadata 
        )
        if not self.get_user(identifier=identifier):
            self.session.add(user)
            self.session.commit()
            # self.session.refresh(user)
            self.session.expunge_all()
            self.session.close()
            return user
        
        return self.get_user(identifier=identifier)
    
    def get_user(self, identifier: str):
        # Main.logger().info(f"Getting user with {identifier}")
        user = self.session.query(User).filter(User.identifier == identifier)
        # Main.logger().info(f"GOT {user.first().id}")
        return user.first()
    
    def get_user_by_id(self, userId: str):
        # Main.logger().info(f"Getting user with {identifier}")
        user = self.session.query(User).filter(User.id == userId)
        # Main.logger().info(f"GOT {user.first().id}")
        if user:
            return user.first()
    
    def update_user(self, id: str, metadata: dict):
        # Main.logger().info(f"Updating user with {id}")
        user = self.session.query(User).filter(User.id == id).first()
        if user:
            user.metadata_ = metadata
            self.session.expunge_all()
            self.session.commit()
            self.session.close()
    

class StepCrud():
    def __init__(self) -> None:
        self.session: Session =database_manageer.postgres_db_service().get_db_session()

    def create_step(self, steps):
        """Create a new Step record."""
        step = Step(**steps)
        step_dict = steps
        if not self.get_step(step_id=(steps).get("id")):

            self.session.add(step)
            self.session.commit()
            self.session.close()
            return step
        else:
            # Main.logger().info(f"Updated step : {steps}")
            self.session.query(Step).filter(Step.id == steps.get("id")).update({Step.output : steps.get("output")})
            self.session.commit()
            self.session.close()
        
    def get_steps_per_thread(self, thread_id):
        steps = self.session.query(Step).filter_by(threadId = thread_id).all()
        return steps


    def get_step(self, step_id):
        """Read a Step record by ID."""

        step = self.session.query(Step).filter(Step.id == step_id).first()
        return step
    
    def delete_step(self,step_id):
        """Delete a Step record by ID."""
        step = self.session.query(Step).filter(Step.id == step_id).first()
        if step:
            self.session.delete(step)
            self.session.commit()
            self.session.close()
    
    def upsert_score(self,step_id,value,comment,name,type):

        try:

            step_feedback = {
                "step_id":step_id,
                "value":value,
                "comment":comment,
                "name":name,
                "type":type,
            }
            self.session.query(Step).filter(Step.id == step_id).update({Step.feedback : step_feedback})
            self.session.commit()
            self.session.close()
        except BaseException as e:
            # Main.logger.info(f"feedback error {e} and feedback id {step_id}....{str(step_id)}")
            pass
class ThreadCrud():
    def __init__(self) -> None:
        self.session: Session = database_manageer.postgres_db_service().get_db_session()

    def create_thread(self, id, name, metadata=None, tags=None, participant_id=None, participant_identifier=None):
        """Create a new thread."""

        new_thread = Thread(
            id=id,
            name=name,
            metadata=metadata,
            tags=tags,
            participant_id=participant_id,
            participant_identifier=participant_identifier
        )
        self.session.add(new_thread)
        self.session.commit()
        self.session.close()
        return new_thread

    def read_thread(self,thread_id):
        """Read a thread by ID."""
        thread = self.session.query(Thread).filter_by(id=thread_id).first()
        self.session.close()
        return thread
    
    def read_threads(self, order_by_col, page=1, page_size=10):
    
        offset = (page - 1) * page_size
        threads = (
            self.session.query(Step)
            .order_by(order_by_col)
            .offset(offset)
            .limit(page_size)
            .all()
        )
        self.session.close()
        return threads[0]

    def delete_thread(self,thread_id):
        """Delete a thread by ID."""

        thread = self.session.query(Thread).filter_by(id=thread_id).first()
        if thread:
            self.session.delete(thread)
            self.session.commit()
            self.session.close()

    def upsert_thread(self, id, name, metadata=None, tags=None, participant_id=None, participant_identifier=None):
        """Upsert a thread. Update if exists, else create."""
        existing_thread = self.session.query(Thread).filter(Thread.id ==id).first()

        if existing_thread:
            # Update existing thread
            # Is making the thread entries null 
            # existing_thread.name = name
            # existing_thread.metadata_= metadata
            # existing_thread.tags = tags
            # existing_thread.participantId = participant_id
            # existing_thread.participantIdentifier = participant_identifier
            pass
        else:
            # Create a new thread
            existing_thread = Thread(
                id=id,
                name=name,
                metadata_=metadata,
                tags=tags,
                participantId=participant_id,
                participantIdentifier=participant_identifier
            )
            self.session.add(existing_thread)

        # self.session.merge(existing_thread)
        self.session.commit()
        self.session.close()
        return existing_thread
    
    def thread_history(self, userId):
        threads = self.session.query(Thread).filter(Thread.participantId == userId).limit(100).all()

        thread_history = []

        # offset = (page - 1) * page_size
        # threads = (
        #     self.session.query(Step)
        #     .order_by(order_by_col)
        #     .offset(offset)
        #     .limit(page_size)
        #     .all()
        # )

        for thread in threads:
            thread_id = thread.id
            thread = thread.to_dict()
            steps = self.session.query(Step).filter(Step.threadId == thread_id).all()
            thread['steps'] = [step.to_dict() for step in steps]
            thread_history.append(thread)

        return thread_history