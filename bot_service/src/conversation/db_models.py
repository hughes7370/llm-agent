from sqlalchemy import inspect,Boolean, Column, ForeignKey, Integer, String, JSON, DateTime
from sqlalchemy.orm import relationship, Session
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base
import json

from common.service_management import Service
from database.manager import DatabaseServiceManager
from common.base import Main

# from conversation.controller import ConversationRestController

Base = declarative_base()
# Base = ConversationRestController().get_conversation_base()
# Base = Main.storage().get_base()
# Main.logger().info("base")

class User(Base):
    __tablename__ = "converse_users"

    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_onupdate=func.now())

    threads = relationship("Thread", back_populates="users")

    def object_as_dict(obj):
        return {
            c.key: getattr(obj, c.key)
            for c in inspect(obj).mapper.column_attrs
        }

class Thread(Base):
    __tablename__ = "converse_threads"

    id = Column(Integer, primary_key=True)
    context = Column(JSON, default=lambda: {})
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_onupdate=func.now())
    user_id = Column(Integer,ForeignKey('converse_users.id'))

    users = relationship("User", back_populates="threads")

    def object_as_dict(obj):
        return {
            c.key: getattr(obj, c.key)
            for c in inspect(obj).mapper.column_attrs
        }

class ConversationModelService(Service):

    def __init__(self, database_service_manager: DatabaseServiceManager) -> None:
        super().__init__()
        self.database_manager = database_service_manager

    async def prepare(self):
        Base = self.database_manager.postgres_db_service().base

        base = Main.storage().get_base()
        if base:
            Main.logger().info("Trying creating base tables for converse..")

        
        class User(Base):
            __tablename__ = "converse_users"

            id = Column(Integer, primary_key=True)
            email = Column(String, unique=True, index=True)
            username = Column(String, unique=True, index=True)
            hashed_password = Column(String)
            is_active = Column(Boolean, default=True)
            created_at = Column(DateTime, server_default=func.now())
            updated_at = Column(DateTime, server_onupdate=func.now())

            threads = relationship("Thread", back_populates="users")

            def object_as_dict(obj):
                return {
                    c.key: getattr(obj, c.key)
                    for c in inspect(obj).mapper.column_attrs
                }

        class Thread(Base):
            __tablename__ = "converse_threads"

            id = Column(Integer, primary_key=True)
            context = Column(JSON, default=lambda: {})
            created_at = Column(DateTime, server_default=func.now())
            updated_at = Column(DateTime, server_onupdate=func.now())
            user_id = Column(Integer,ForeignKey('converse_users.id'))

            users = relationship("User", back_populates="threads")

            def object_as_dict(obj):
                return {
                    c.key: getattr(obj, c.key)
                    for c in inspect(obj).mapper.column_attrs
                }
        
        try:
            if base:
                Main.logger().info("Trying creating base tables for conversation controller..")
                Base.metadata.create_all(bind=self.database_manager.postgres_db_service().engine)
                Main.logger().info(" Created base tables for conversation controller..")

        except BaseException as e:
                error = {"ERROR": e}
                Main.logger().critical(f"Could not create base tables for conversation controller due to \n {error}, db operation won't work !")

    def get_user(self, db: Session, username: str = None):
        db_user = db.query(User).filter(User.username == username).first()
        return db_user

    def upsert_converse_thread(self, db: Session, thread_id: int, thread_context: tuple[str,str] = None, username: str = None):
        
        db_thread = self.get_converse_thread(db, thread_id=thread_id)
        db_user = self.get_user(db, username=username)
        
        if db_thread:
            db_thread_context = json.loads(db_thread.context)
            list_of_queries = db_thread_context.get("queries",[])
            list_of_queries.append(thread_context)

            db.query(Thread).filter(Thread.id == thread_id).update({'context': json.dumps({"queries":list_of_queries})} )
            db.commit()
            return thread_id

        db_thread = Thread(context = json.dumps({"queries":[thread_context]}), user_id= db_user.id)
        db.add(db_thread)
        db.commit()

        return db_thread.id
        

    def get_converse_thread(self, db: Session, thread_id: int) -> Thread | None:
        return db.query(Thread).filter(Thread.id == thread_id).first()
        