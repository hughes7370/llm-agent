from pydantic.v1 import BaseModel as PydanticBaseModel
from typing import Any, Optional
from langchain.memory import ConversationBufferWindowMemory
from enum import Enum

class ExtendedEnum(Enum):

    @classmethod
    def list(cls):
        return list(map(lambda c: c.value, cls))


class BaseModel(PydanticBaseModel):
    """Base model for all data models"""
    class Config:
        populate_by_name = True
        validate_assignment = True
        arbitrary_types_allowed = True
        protected_namespaces = ()


class LoggerConfiguration(BaseModel):
    """Represents the logger configuration"""
    log_level: str

class ServerConfiguration(BaseModel):
    """Represents the server configuration"""
    host: str
    port: str

class OpenAIConfiguration(BaseModel):
    """Represents the OpenAI configuration"""
    api_key: str
    model_name: str

class AzureAIConfiguration(BaseModel):
    """Represents the AzureAI configuration"""
    api_key: str 
    type: str
    base: str
    version: str
    deployment_name: str
    embedding_deployment_name: str
    model_name: str

class PerplexityAIConfiguration(BaseModel):
    """Represents the Perplexity configuration"""
    api_key: str
    model_name: str
    api_base: str

class AnthropicAIConfiguration(BaseModel):
    """Represents the Anthropic configuration"""
    api_key: str
    model_name: str

class VectorDBConfiguration(BaseModel):
    """Represents vectorDB configuration"""
    database_directory: str
    embeddings_json_file: str


class APIHandlerConfiguration(BaseModel):
    """Represents the APIHandler configuration"""
    token: str
    actor_name: str
    openapi_spec_dir: str

class TranformerConfiguration(BaseModel):
    """Represents the Tranformer configuration"""
    filter_keys_dir: str

class UserConfiguration(BaseModel):
    """Represents the User configuration"""
    user_directory: str

class PostgreSQLConfiguation(BaseModel):
    """Represents the MongoDB configuration"""
    host: str
    port: int
    username: str
    password: str
    db: str

class MongoDBConfiguation(BaseModel):
    """Represents the MongoDB configuration"""
    host: str
    port: int
    username: str
    password: str
    db: str

class LLMResponseFormatConfiguration(BaseModel):
    planner_schema: str
    api_generator_schema: str

class StorageConfiguration(BaseModel):
    """Represents the Storage configuration"""
    storage_type: str = "Postgres"

class CommonConfiguration(BaseModel):
    max_retries: int
    llm_logs_dir: str
    llm_pr_queries_file: str

class Configuration(BaseModel):
    """Represents the configuration"""
    application_name: str
    logger_configuration: LoggerConfiguration
    openai_configuration: OpenAIConfiguration
    server_configuration: ServerConfiguration
    azureai_configuration: AzureAIConfiguration
    perplexityai_configuration :PerplexityAIConfiguration
    anthropicai_configuration :AnthropicAIConfiguration
    vectorDB_configuration: VectorDBConfiguration
    api_handler_configuration: APIHandlerConfiguration
    common_configuration:  CommonConfiguration
    user_configuration: UserConfiguration
    transformer_configuration: TranformerConfiguration
    postgresql_configuration: PostgreSQLConfiguation
    mongodb_configuration: MongoDBConfiguation
    llm_response_format_configuration: LLMResponseFormatConfiguration


class QueryContext(BaseModel):
    """Represents the query context"""
    query: str
    role: str
    stream_response: Any
    conversation_context: Optional[ConversationBufferWindowMemory] = None


# region Constants

class Roles(ExtendedEnum):
    "Represents roles"
    admin: str = "Admin"
    Basic: str = "Normal"
    Developer: str = "Developer"

class LLMProvider(ExtendedEnum):
    "Represents provider"
    openai: str = "openai"
    azure_openai: str = "azure_openai"
    perplexity_ai: str = "perplexity_ai"
    anthropic_ai: str = "anthropic_ai"

class PlannerEnum(ExtendedEnum):
    "Represents different planner prompts"
    planner_with_apis : str = "planner_withAPIs"
    planner_with_claude: str = "planner_pureClaude"

# endregion