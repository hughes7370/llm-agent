from common.base import Main
from common.service_management import Service, ServiceManager
from pymongo import MongoClient, errors

from sqlalchemy.engine import URL
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from dotenv import load_dotenv, find_dotenv

from sqlalchemy.orm.session import Session

class MongoDBService(Service):
    
    def __init__(self:str) -> None:

        super().__init__()
        # self.client = MongoClient(host=Main.configuration().mongodb_configuration.host, port=Main.configuration().mongodb_configuration.port, username=Main.configuration().mongodb_configuration.username, password=Main.configuration().mongodb_configuration.password)
        self.client = MongoClient(host=Main.configuration().mongodb_configuration.host, port=Main.configuration().mongodb_configuration.port,)
        self.db = self.client.get_database(Main.configuration().mongodb_configuration.db)

    def create_collection_using_docs(self, collection_name:str, documents: list[dict]):
        """
        Create a new collection and populate it with documents.

        This method creates a new collection within an object's associated database with the specified name 
        and populates it with the provided list of dictionaries representing the documents.

        Parameters:
            collection_name (str): The name of the collection to be created.
            documents (list[dict]): A list of dictionaries where each dictionary is a document that 
                                    will be inserted into the collection upon creation.

        Returns:
            object: An instance or reference to the newly created collection, or detailed information about
                    the success/failure of the operation. The exact return type can depend on the database
                    system being used.
        """

        collection = self.db.get_collection(name=collection_name)
        try:
            ack = collection.insert_many(documents)
            return ack.acknowledged
        
        except errors.PyMongoError as f:
            error_msg = f"Some error occured while creating mongo collection named {collection_name} with {len(documents)} documents with error {f}."
            Main.logger().debug(error_msg,exc_info=1)
            raise errors.PyMongoError(str(error_msg))

    def drop_collection(self, collection_name: str):
        """
        Drop or delete the specified collection from the database.

        Attempts to remove an existing collection along with all its documents from the database linked
        to this instance. If the operation is successful, an acknowledgment is returned. If any error
        occurs during the process, a message is logged with the error details and no exception is
        raised to the caller.

        Parameters:
        ----------
        collection_name : str
            The name of the collection that needs to be dropped.

        Returns:
        -------
        dict or bool
            An acknowledgment from the drop operation which typically contains information like whether
            the command was acknowledged by the server. May return a boolean `True` if the operation
            does not generate an acknowledgment object but was successful.
        """

        try:
            ack = self.db.drop_collection(name_or_collection=collection_name)
            return ack
        except errors.PyMongoError as f:
            error_msg = f"Some error occurred while dropping mongo collection named {collection_name} with error {f}"
            Main.logger().debug(error_msg, exc_info=1)
            raise errors.PyMongoError(str(error_msg))

    def run_aggregation_pipeline(self, collection_name: str, pipeline: list):
        """
        Executes an aggregation pipeline on the specified MongoDB collection.
    
        This method applies a sequence of data aggregation operations (stages) to transform and
        combine documents in the specified collection.
    
        Parameters:
        ----------
        collection_name : str
            The name of the collection to perform the aggregation on.
        pipeline : list
            A list of aggregation pipeline stages to be applied to the collection.
    
        Returns:
        -------
        list
            A list of dictionaries representing the documents that result from the aggregation.
    
        Raises:
        ------
        errors.PyMongoError
            If a PyMongo-related error occurs during the aggregation pipeline execution.
        """
    
        collection = self.db.get_collection(collection_name)
        try:
            aggregate_cursor = collection.aggregate(pipeline)
            aggregate_results = []
            for result in aggregate_cursor:
                if '_id' in result.keys():
                    result['_id'] = str(result['_id'])
                aggregate_results.append(result)

            Main.logger().info(f"Length of the aggregate results {len(aggregate_results)}")
    
            return aggregate_results
        except errors.PyMongoError as f:
            error_msg = f"Some error occurred while running mongo aggregation pipeline for collection {collection_name} " \
                        f"with steps {len(pipeline)} and error {f}"
            Main.logger().debug(error_msg, exc_info=1)
            raise errors.PyMongoError(str(error_msg))
    

class PostgresDBService(Service):
    
    def __init__(self) -> None:
        super().__init__()

        SQLALCHEMY_DATABASE_URL = URL.create(
            drivername='postgresql',
            username=Main.configuration().postgresql_configuration.username,
            password=Main.configuration().postgresql_configuration.password,
            host=Main.configuration().postgresql_configuration.host,
            port=Main.configuration().postgresql_configuration.port,
            database=Main.configuration().postgresql_configuration.db
        )

        self.engine = create_engine(SQLALCHEMY_DATABASE_URL,pool_size=5,max_overflow=10,pool_pre_ping=True, )
        self.base = declarative_base()


    def get_db_session(self):
            sessionlocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine, expire_on_commit=False)
            db = sessionlocal()
            return db
    
    def get_db(self):
        db = sessionmaker(autocommit=False, autoflush=False, bind=self.engine, expire_on_commit=False)
        try:
            yield db
        finally:
            db.close()

class DatabaseServiceManager(ServiceManager):
    def __init__(self) -> None:
        super().__init__()
        self._mongo_db_service = MongoDBService()
        self._postgres_db_service = PostgresDBService()

    def mongo_db_service(self):
        return self._mongo_db_service
 
    def postgres_db_service(self):
        return self._postgres_db_service