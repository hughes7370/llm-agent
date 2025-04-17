from common.service_management import ServiceManager, Service
from langchain_openai import OpenAIEmbeddings, AzureOpenAIEmbeddings, ChatOpenAI, AzureChatOpenAI
from openai import AsyncAzureOpenAI, AsyncOpenAI, OpenAI, AzureOpenAI
from anthropic import Anthropic, AsyncClient as AnthropicAsyncClient , types as AnthropicTypes
from common.base import Main
from common.data_model import Roles, LLMProvider
import os
import tiktoken
from typing import Any
from datetime import datetime
import csv
from store.prompts import PromptStore
from pathlib import Path

class MyCustomPrompt():
    def __init__(self, my_custom_value):
        self.text = f"Custom prompt {my_custom_value}"


class AzureOpenAIService(Service):
    
    def __init__(self):
        super().__init__() 
        self.api_type = Main.configuration().azureai_configuration.type
        self.api_key = Main.configuration().azureai_configuration.api_key
        self.api_base = Main.configuration().azureai_configuration.base
        self.api_version = Main.configuration().azureai_configuration.version
        self.deployment_name = Main.configuration().azureai_configuration.deployment_name
        self.model_name = Main.configuration().azureai_configuration.model_name
        self.embedding_deployment_name = Main.configuration().azureai_configuration.embedding_deployment_name
        self.prompts = PromptStore()

    def set_client_by_model(self, **kwargs):
        self.api_type = kwargs.get("api_type")
        self.api_key = kwargs.get("api_key")
        self.api_base = kwargs.get("api_base")
        self.api_version = kwargs.get("api_version")
        self.deployment_name = kwargs.get("deployment_name")
        self.model_name = kwargs.get("model_name")
        self.embedding_deployment_name = kwargs.get("embedding_deployment_name")

    async def token_counter(self,response: str) -> int:
        enc = tiktoken.encoding_for_model(self.model_name)
        return len(enc.encode(response))

    async def acompletion(
        self,
        prompt: str,
        stream_response: Any,
        role: str = Roles.admin.value,
        system_message: str = "You are a helpful ai assistent",
        **kwargs
    ):
        tokens = []
        client = AsyncAzureOpenAI(
            api_key=self.api_key,
            azure_endpoint=self.api_base,
            api_version=self.api_version,
        )
        async for stream_resp in await client.chat.completions.create(
            model=self.deployment_name,
            temperature = 0,
            stream=True,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt},
            ],
            **kwargs
        ):
            if stream_resp.choices and stream_resp.choices[0].delta.content:
                token = stream_resp.choices[0].delta.content
                model_name = self.model_name
                tokens.append(token)
                await stream_response(token)
                
        if role == Roles.Developer.value:
            await self.log_llm_responses(prompt, "".join(tokens), self.model_name)

        return "".join(tokens)
   
    async def completion(self, prompt:str, role:str, system_message:str = "You are a helpful ai assistent",**kwargs):
        client = AzureOpenAI(
            api_key=self.api_key,
            azure_endpoint=self.api_base,
            api_version=self.api_version,
        )

        response = client.chat.completions.create(
            # engine = self.deployment_name,
            temperature=0,
            model=self.deployment_name,
            messages =  [
                {"role": "system","content": system_message},
                {"role": "user", "content": prompt },
                ],
                **kwargs) 

        llm_response = response.choices[0].message.content.strip()
        Main.logger().info(f"*** Response from openAI *** {llm_response} ")

        if role == Roles.Developer.value:
            await self.log_llm_responses(prompt, llm_response, self.model_name)
        return llm_response

    async def log_llm_responses(self, prompt: str, response: str, model_name: str):
        current_date = datetime.now().strftime("%Y-%m-%d")
        
        llm_log_dir = Path(Main.configuration().common_configuration.llm_logs_dir)
        llm_log_dir.mkdir(exist_ok=True)


        file_name = "llm_logs_"+current_date+".csv"
        file_path = llm_log_dir / file_name

        row = [prompt, response, model_name]
        if (os.path.isfile(file_path)):
            with open(file_path, "a") as write_object:
                csv.writer(write_object).writerow(row)
        else:
            with open(file_path, "a") as write_object:
                init_row=["Prompt", "Response", "Model Name", "\n"]
                write_object.write(','.join(map(str, init_row)))

    async def get_llm(self):
        llm = AzureChatOpenAI(
            azure_deployment=self.deployment_name, 
            model=self.model_name,
            api_key=self.api_key, 
            azure_endpoint=self.api_base,
            api_version=self.api_version,
        )
        return llm

    async def get_embeddings(self,**kwargs):
        Main.logger().info(f"Getting embeddings using {self.__class__.__name__}..")

        embedding_function = AzureOpenAIEmbeddings(
            azure_deployment=self.embedding_deployment_name,
            azure_endpoint=self.api_base,
            api_key=self.api_key,
            api_version=self.api_version,
            **kwargs)
        
        return embedding_function

class OpenAIService(Service):
    def __init__(self):
        super().__init__() 
        self.api_key = Main.configuration().openai_configuration.api_key
        self.model_name = Main.configuration().openai_configuration.model_name
        self.prompts = PromptStore()

    def set_client_by_model(self, model_name: str, **kwargs):
        self.model_name = model_name
    
    async def acompletion(
        self,
        prompt: str,
        stream_response: Any,
        role: str,
        system_message: str = "You are a helpful ai assistent", **kwargs
    ):
        tokens = []
        client = AsyncOpenAI(
            api_key=self.api_key,
        )
        async for stream_resp in await client.chat.completions.create(
            model=self.model_name,
            temperature = 0,
            stream=True,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt},
            ],
            **kwargs
        ):
            if stream_resp.choices and stream_resp.choices[0].delta.content:
                token = stream_resp.choices[0].delta.content
                model_name = self.model_name 
                tokens.append(token)
                await stream_response(token)

        if role == Roles.Developer.value:
            await self.log_llm_responses(prompt, "".join(tokens), self.model_name)

        return "".join(tokens)

    async def completion(self, prompt:str,role: str,system_message:str = "You are a helpful ai assistent",**kwargs):

        client = OpenAI(api_key=self.api_key)
        response = client.chat.completions.create(
            model=self.model_name,
            messages =  [
                {"role": "system","content": system_message},
                {"role": "user", "content": prompt },
                ]
                ,temperature=0,
                **kwargs) 

        llm_response = response.choices[0].message.content.strip()
        Main.logger().info(f"*** Response from openAI *** {llm_response} ")
        
        if role == Roles.Developer.value:
            await self.log_llm_responses(prompt, llm_response, self.model_name)
        return llm_response
    
    async def get_llm(self):
        llm = ChatOpenAI(
            temperature=0,
            openai_api_key=self.api_key
        )
        return llm
    
    async def get_embeddings(self,**kwargs):
        Main.logger().info(f"Getting embeddings using {self.__class__.__name__}")
        embedding_function = OpenAIEmbeddings(
                openai_api_key=self.api_key,
                **kwargs,)
        
        return embedding_function

    async def token_counter(self,response: str) -> int:
        enc = tiktoken.encoding_for_model(self.model_name)
        return len(enc.encode(response))
    
    async def log_llm_responses(self, prompt: str, response: str, model_name: str):
        current_date = datetime.now().strftime("%Y-%m-%d")
        
        llm_log_dir = Path(Main.configuration().common_configuration.llm_logs_dir)
        llm_log_dir.mkdir(exist_ok=True)


        file_name = "llm_logs_"+current_date+".csv"
        file_path = llm_log_dir / file_name

        row = [prompt, response, model_name]
        if (os.path.isfile(file_path)):
            with open(file_path, "a") as write_object:
                csv.writer(write_object).writerow(row)
        else:
            with open(file_path, "a") as write_object:
                init_row=["Prompt", "Response", "Model Name", "\n"]
                write_object.write(','.join(map(str, init_row)))

class PreplexityAIService(Service):
    def __init__(self):
        super().__init__() 
        self.api_key = Main.configuration().perplexityai_configuration.api_key 
        self.model_name = Main.configuration().perplexityai_configuration.model_name
        self.prompts = PromptStore()

    async def acompletion(
        self,
        prompt: str,
        stream_response: Any,
        role: str,
        system_message: str = "You are a very helpful ai assistant", **kwargs
    ):
        tokens = []
        client = AsyncOpenAI(
            api_key=self.api_key,
            base_url = Main.configuration().perplexityai_configuration.api_base,
        )

        async for stream_resp in await client.chat.completions.create(
            model=self.model_name,
            temperature = 0,
            stream=True,
            messages=[
                {"role": "user", "content": prompt},
            ],
            **kwargs
        ):
            if stream_resp.choices and stream_resp.choices[0].delta.content:
                token = stream_resp.choices[0].delta.content
                model_name = self.model_name 
                tokens.append(token)
                await stream_response(token)

        if role == Roles.Developer.value:
            await self.log_llm_responses(prompt, "".join(tokens), self.model_name)

        return "".join(tokens)

    async def completion(self, prompt:str,role: str,system_message:str = "You are a very helpful ai assistent",**kwargs):

        client = OpenAI(
            base_url = Main.configuration().perplexityai_configuration.api_base,
            api_key=self.api_key
        )
        
        response = client.chat.completions.create(
            model=self.model_name,
            messages =  [
                {"role": "user", "content": prompt },
                ]
                ,temperature=0,
                **kwargs) 

        llm_response = response.choices[0].message.content.strip()
        Main.logger().info(f"*** Response from Perplexity *** {llm_response} ")
        
        if role == Roles.Developer.value:
            await self.log_llm_responses(prompt, llm_response, self.model_name)
        return llm_response

    def set_client_by_model(self, model_name: str, **kwargs):
        self.model_name = model_name
    
    async def token_counter(self,response: str) -> int:
        enc = tiktoken.encoding_for_model("gpt-4")
        return len(enc.encode(response))
    
    async def log_llm_responses(self, prompt: str, response: str, model_name: str):
        current_date = datetime.now().strftime("%Y-%m-%d")
        
        llm_log_dir = Path(Main.configuration().common_configuration.llm_logs_dir)
        llm_log_dir.mkdir(exist_ok=True)


        file_name = "llm_logs_"+current_date+".csv"
        file_path = llm_log_dir / file_name

        row = [prompt, response, model_name]
        if (os.path.isfile(file_path)):
            with open(file_path, "a") as write_object:
                csv.writer(write_object).writerow(row)
        else:
            with open(file_path, "a") as write_object:
                init_row=["Prompt", "Response", "Model Name", "\n"]
                write_object.write(','.join(map(str, init_row)))

class AnthropicAIService(Service):
    
    def __init__(self) -> None:
        super().__init__()
        self.api_key = Main.configuration().anthropicai_configuration.api_key
        self.model_completion = Main.configuration().anthropicai_configuration.model_name
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

    async def log_llm_responses(self, prompt: str, response: str, model_name: str):
        current_date = datetime.now().strftime("%Y-%m-%d")
        
        llm_log_dir = Path(Main.configuration().common_configuration.llm_logs_dir)
        llm_log_dir.mkdir(exist_ok=True)


        file_name = "llm_logs_"+current_date+".csv"
        file_path = llm_log_dir / file_name

        row = [prompt, response, model_name]
        if (os.path.isfile(file_path)):
            with open(file_path, "a") as write_object:
                csv.writer(write_object).writerow(row)
        else:
            with open(file_path, "a") as write_object:
                init_row=["Prompt", "Response", "Model Name", "\n"]
                write_object.write(','.join(map(str, init_row)))
                
    async def completion(self, prompt:str,role: str,system_message:str = "You are a very helpful ai assistent",**kwargs):
        
        client = Anthropic(api_key=self.api_key)
        
        response = client.messages.create(
            model=self.model_completion,
            temperature=0,
            system=system_message,
            # stream=True,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }
            ],
            **kwargs
        )

        llm_response = response.content[0].text.strip()
        Main.logger().info(f"*** Response from Anthropic *** {llm_response} ")
        
        if role == Roles.Developer.value:
            await self.log_llm_responses(prompt, llm_response, self.model_name)
        return llm_response

    async def acompletion(self,prompt: str,stream_response: Any,role: str,system_message: str = "You are a very helpful ai assistent", **kwargs):
        
        tokens = []
        client = AnthropicAsyncClient(api_key=self.api_key)

        async for stream_resp in await client.messages.create(
            model=self.model_completion,
            temperature=0,
            system=system_message,
            stream=True,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }
            ],
            **kwargs
        ):
            if isinstance(stream_resp, AnthropicTypes.content_block_delta_event.ContentBlockDeltaEvent) and stream_resp.delta.text:
                token = stream_resp.delta.text
                model_name = self.model_name 
                tokens.append(token)
                await stream_response(token)

        if role == Roles.Developer.value:
            await self.log_llm_responses(prompt, "".join(tokens), self.model_name)

        return "".join(tokens)
      
    
    def set_client_by_model(self, model_name: str, **kwargs):
        self.model_name = model_name

class LLMServiceManager(ServiceManager):

    def __init__(self):
        super().__init__()
        self._azure_openai_service= AzureOpenAIService()
        self._openai_service = OpenAIService()
        self._perplexity_service = PreplexityAIService()
        self._anthropic_service = AnthropicAIService()

    def azure_openai_service(self):
        return self._azure_openai_service

    def openai_service(self):
        return self._openai_service
    
    def perplexity_service(self):
        return self._perplexity_service
    
    def anthropic_service(self):
        return self._anthropic_service

    def get_service(self,llm_provider: LLMProvider, model_name: str, **kwargs ):
        match llm_provider:
            
            case LLMProvider.openai.value:
                self._openai_service.set_client_by_model(model_name=model_name, **kwargs)
                return self._openai_service
            
            case LLMProvider.azure_openai.value:
                self._azure_openai_service.set_client_by_model(model_name=model_name, **kwargs)
                return self._azure_openai_service
            
            case LLMProvider.perplexity_ai.value:
                self._perplexity_service.set_client_by_model(model_name=model_name, **kwargs)
                return self._perplexity_service
            
            case LLMProvider.anthropic_ai.value:
                self._anthropic_service.set_client_by_model(model_name=model_name, **kwargs)
                return self._anthropic_service
            
            