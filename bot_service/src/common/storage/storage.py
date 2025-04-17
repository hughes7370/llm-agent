"""Defines controller"""

from common.service_management import  Service
from common.data_model import StorageConfiguration
from enum import Enum

from sqlalchemy.engine import URL
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.session import Session

from dotenv import load_dotenv, find_dotenv
import os


_ = load_dotenv(find_dotenv(filename='.env'))

class StorageType(Enum):
    postgres: str = "Postgres"
    mongo_db: str = "MongoDB"


class StorageService(Service):

    """Implements a base Storage service"""
    def __init__(self, storage: StorageConfiguration):
        super().__init__()

        # Data model not created as this might be temproprary
        POSTGRES_USER = os.getenv('POSTGRES_USER','NOT_PROVIDED_POSTGRES_USER')
        POSTGRES_PW = os.getenv('POSTGRES_PW','NOT_PROVIDED_POSTGRES_PW')
        POSTGRES_HOST = os.getenv('POSTGRES_HOST','NOT_PROVIDED_POSTGRES_HOST')
        POSTGRES_PORT = os.getenv('POSTGRES_PORT',2)
        POSTGRES_DB = os.getenv('POSTGRES_DB','NOT_PROVIDED_POSTGRES_DB')

        SQLALCHEMY_DATABASE_URL = URL.create(
            drivername='postgresql',
            username=POSTGRES_USER,
            password=POSTGRES_PW,
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
            database=POSTGRES_DB
        )

        self.engine = create_engine(SQLALCHEMY_DATABASE_URL,pool_size=5,max_overflow=10,pool_pre_ping=True)
        self.base = declarative_base()

    def prepare(self) -> None:
        """Prepares the service"""
        self.connect()

        # destroy
        self.disconnect()

    async def connect(self):
        pass
    
    async def disconnect(self):
        pass

    def execute(self, sqlalc_obj):
        pass

    def get_base(self):
        return self.base