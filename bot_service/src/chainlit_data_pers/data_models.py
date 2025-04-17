from database.manager import DatabaseServiceManager
from common.base import Main
import datetime
from chainlit.step import StepDict

from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, JSON, ARRAY, Table, Boolean
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import relationship, class_mapper


database_manageer = DatabaseServiceManager()
Base = database_manageer.postgres_db_service().base
engine = database_manageer.postgres_db_service().engine

class User(Base):
    __tablename__ = 'users'

    id = Column(String(100), primary_key=True)
    identifier = Column(String(100), nullable=False, unique=True)
    createdAt = Column("createdAt",DateTime(), default=datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%d %H:%M:%S"))
    updatedAt = Column("updatedAt",DateTime(), default=datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%d %H:%M:%S"), onupdate=datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%d %H:%M:%S"))
    metadata_ = Column("metadata_",JSON, default=lambda: {})

class Step(Base):
    __tablename__ = 'steps'

    name = Column(String)
    type = Column(String)
    id = Column(String, primary_key=True)
    threadId = Column("threadId",String)
    parentId = Column("parentId",String, ForeignKey('steps.id'))
    disableFeedback = Column("disableFeedback",Boolean)
    streaming = Column("streaming",Boolean)
    waitForAnswer = Column("waitForAnswer",Boolean)
    isError = Column("isError",Boolean)
    metadata_ = Column("metadata_",JSON, default=lambda: {})
    input = Column(JSON,default=lambda: {})
    output = Column(JSON,default=lambda: {})
    createdAt = Column("createdAt",String, default=datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%d %H:%M:%S"))
    start = Column(String)
    end = Column(String)
    generation =  Column(JSON,default=lambda: {})
    showInput = Column(String)
    language = Column(String)
    indent = Column(Integer)
    feedback = Column(JSON,default=lambda: {})
    tags = Column(JSON,default=lambda: {})
    attachments = Column(ARRAY(JSON)) 

    def to_dict(self):
        """
        Convert model instance into a dictionary
        """
        return {col.key: getattr(self, col.key) 
                for col in class_mapper(self.__class__).mapped_table.columns}

thread_steps_association = Table(
    'thread_steps_association',
    Base.metadata,
    Column('thread_id', String, ForeignKey('threads.id')),
    Column('step_id', String, ForeignKey('steps.id'))
)

class Thread(Base):
    __tablename__ = 'threads'

    id = Column(String, primary_key=True)
    createdAt = Column("createdAt",String, default=datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%d %H:%M:%S"))
    name = Column(String)
    metadata_ = Column("metadata_",JSON, default=lambda: {})  # Using JSONB for dictionary storage, specific to PostgreSQL
    tags = Column(ARRAY(String))  # Using ARRAY, specific to PostgreSQL
    elements = Column(ARRAY(JSON)) 
    steps = relationship("Step", secondary=thread_steps_association)  # Define relationship if Step model exists
    participantId = Column("participantId",String,nullable=True)
    participantIdentifier = Column("participantIdentifier",String, nullable=True)

    def to_dict(self):
        """
        Convert model instance into a dictionary
        """
        return {col.key: getattr(self, col.key) 
                for col in class_mapper(self.__class__).mapped_table.columns}
        #  return {item.id: item for item in item_list}

try:
    Base.metadata.create_all(engine)
except OperationalError as e:
    Main.logger().critical(f"Skipping data connection .. data persistence will not work !")