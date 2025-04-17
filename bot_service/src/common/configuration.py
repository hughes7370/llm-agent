"""Implements the default configuration"""

import os
from common.data_model import Configuration as ConfigurationModel


class Configuration:
    """Represents the default configuration"""

    def __init__(self):
        config_obj = {
            "application_name": os.environ.get("APPLICATION_NAME", "bot_service"),
            "logger_configuration": {
                "log_level": os.environ.get("LOG_LEVEL", "DEBUG")
            },
            "server_configuration": {
                "host": os.environ.get("HOST", "0.0.0.0"),
                "port": os.environ.get("PORT", "8080"),
            },
            "openai_configuration": {
                "api_key": os.environ.get("OPENAI_API_KEY"),
                "model_name":os.environ.get("OPENAI_MODEL_NAME")

            },
            "azureai_configuration":{
                "api_key": os.environ.get("AZURE_API_KEY"),
                "type":os.environ.get("AZURE_API_TYPE"),
                "base":os.environ.get("AZURE_API_BASE"),
                "version":os.environ.get("AZURE_API_VERSION"),
                "deployment_name":os.environ.get("AZURE_DEPLOYMENT_NAME"),
                "embedding_deployment_name":os.environ.get("AZURE_EMBEDDING_DEPLOYMENT_NAME"),
                "model_name":os.environ.get("AZURE_MODEL_NAME")
                
            },
            "perplexityai_configuration": {
                "api_key": os.environ.get("PERPLEXITY_API_KEY"),
                "model_name":os.environ.get("PERPLEXITY_MODEL_NAME"),
                "api_base":os.environ.get("PERPLEXITY_API_BASE")

            },
            "anthropicai_configuration": {
                "api_key": os.environ.get("ANTHROPIC_API_KEY"),
                "model_name":os.environ.get("ANTHROPIC_MODEL_NAME"),
            },
            "vectorDB_configuration": {
                "database_directory":os.environ.get("DATABSE_DIRECTORY"),
                "embeddings_json_file": os.environ.get('EMBEDDINGS_JSON_FILE'),
            },
            "api_handler_configuration":{
                "token": os.environ.get('TOKEN'),
                "actor_name": os.environ.get('ACTOR_NAME'),
                "openapi_spec_dir": os.environ.get('OPENAPI_SPEC_DIR'),
            },
            "common_configuration":{
                "max_retries": os.environ.get("MAX_RETRIES"),
                "llm_logs_dir": os.environ.get("LLM_LOGS_DIR"),
                "llm_pr_queries_file": os.environ.get("LLM_PR_QUERIES_PATH"),
            },
            "user_configuration":{
                "user_directory": os.environ.get("USER_DIRECTORY")
            },
            "transformer_configuration":{
                "filter_keys_dir": os.environ.get("FILTER_KEYS_DIR")
            },
            "postgresql_configuration":{
                "host": os.environ.get("POSTGRES_HOST"),
                "port": int(os.environ.get("POSTGRES_PORT")),
                "username": os.environ.get("POSTGRES_USERNAME"),
                "password": os.environ.get("POSTGRES_PASSWRD"),
                "db": os.environ.get("POSTGRES_DB"),
            },
            "mongodb_configuration": {
                "host": os.environ.get("MONGODB_HOST","MONGO_HOST_PROVIDED"),
                "port": int(os.environ.get("MONGODB_PORT",0)),
                "username": os.environ.get("MONGODB_USERNAME",""),
                "password": os.environ.get("MONGODB_PASSWORD",""),
                "db": os.environ.get("MONGODB_DB","MONGO_DB_PROVIDED"),
            },
            "llm_response_format_configuration":{
                "planner_schema": os.environ.get("PLANNER_SCHEMA","./store/response_schemas/planner_response.json"),
                "api_generator_schema":os.environ.get("API_GENERATOR_SCHEMA","./store/response_schemas/api_generator_response.json")
            }

        }
        self._configuration = ConfigurationModel.parse_obj(config_obj)

    def configuration(self):
        """Returns the configuration"""
        return self._configuration
