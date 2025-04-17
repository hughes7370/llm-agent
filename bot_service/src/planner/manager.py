import ast
import datetime
import json

import asyncify
import pandas as pd
from api_handler.manager import APIHandlerServiceManager
from common.base import Main
from common.data_model import LLMProvider, QueryContext
from common.service_management import ServiceManager
from common.utils import timeit
from database.manager import DatabaseServiceManager
from LLM.manager import LLMServiceManager
from search.manager import SearchServiceManager
from store.prompts import PromptStore
from transformer.manager import TransformerServiceManager


class PlannerServiceManager(ServiceManager):
    def __init__(self, _llm_service_manager: LLMServiceManager, _api_handler_manager: APIHandlerServiceManager, _search_service_manager: SearchServiceManager, _transformer_service_manager: TransformerServiceManager, _database_service_manager : DatabaseServiceManager):
        super().__init__()
        # Get default model with one of the below clients
        #self.llm = _llm_service_manager.azure_openai_service()
        #self.llm = _llm_service_manager.openai_service()

        # Get custom client with custom model
        self.llm = _llm_service_manager.get_service(llm_provider =  LLMProvider.openai.value, model_name = "gpt-4-turbo")
        self.llm_search = _llm_service_manager.get_service(llm_provider =  LLMProvider.perplexity_ai.value, model_name = "llama-3.1-sonar-large-128k-online")
        self.llm_summerizer= _llm_service_manager.get_service(llm_provider =  LLMProvider.anthropic_ai.value, model_name = "claude-3-opus-20240229")


        # self.llm = _llm_service_manager.get_service(llm_provider =  LLMProvider.azure_openai.value, model_name = Main.configuration().azureai_configuration.model_name,
        #     api_type = Main.configuration().azureai_configuration.type,
        #     api_key = Main.configuration().azureai_configuration.api_key,
        #     api_base = Main.configuration().azureai_configuration.base,
        #     api_version = Main.configuration().azureai_configuration.version,
        #     deployment_name = Main.configuration().azureai_configuration.deployment_name,
        #     embedding_deployment_name = Main.configuration().azureai_configuration.embedding_deployment_name,
        # )

        self.prompts = PromptStore()
        self.api_handler = _api_handler_manager
        self.search_manager = _search_service_manager
        self.transformer_manager = _transformer_service_manager
        self.database_manager = _database_service_manager.mongo_db_service()
        self.llm_manager = _llm_service_manager
        #Need to indent the JSON for higher prompt performance
        with open(Main.configuration().llm_response_format_configuration.planner_schema,"r") as f:
            self.planner_schema = json.dumps(json.load(f),indent=3)
            
        with open(Main.configuration().llm_response_format_configuration.api_generator_schema,"r") as f:
            self.api_generator_schema = json.load(f) 

    @timeit
    async def planner(self, query_context: QueryContext,role: str, planner_name: str = "planner_withAPIs") -> str:
        """Creates step-by-step tasks to be executed for the input query. Response is in JSON mode"""
        knowledge_base_search = await self.search_manager.search(query_context.query,"knowledgebase")
        Main.logger().info(f"\n\n\n Knowledge base search result: {knowledge_base_search}")
        stream_response = query_context.stream_response
        prompt = self.prompts.prompt(planner_name).get("text")
        query = query_context.query
        context = query_context.conversation_context
        final_prompt = prompt.format(query=query, context=context, datetime=datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%d %H:%M:%S"), knowledge = knowledge_base_search, response_schema = self.planner_schema)
        #Getting the response in JSON mode
        # Main.logger().info(f"\n\n\n\n Final Planner prompt {final_prompt} ")
        #response = await self.llm.acompletion(final_prompt,stream_response, role=role, response_format={ "type": "json_object" })
        response = await self.llm_summerizer.acompletion(final_prompt,stream_response, role=role, max_tokens = 4096)
        return response


    @timeit
    async def global_search(self, task: str, role: str, search_information: str) :
        Main.logger().info(f"Length of search information is {len(search_information)} and type {type(search_information)}")
        
        prompt = self.prompts.prompt("global_search").get("text")
        final_prompt = prompt.format(task=task, search_information = search_information)

        response = await self.llm_search.completion(final_prompt, role=role)
        return response

    @timeit
    async def summarizer(self, object: any, task: str, stream_response: any, role: str) -> str:
        """Summarizes the end result for the user"""
        Main.logger().info("Entered Summarizer Task")

        # Get custom client with custom model
        #self.llm = self.llm_manager.get_service(llm_provider =  LLMProvider.openai.value, model_name = "gpt-3.5-turbo")

        prompt = self.prompts.prompt("summarizer").get("text") 
        final_prompt = prompt.format(transformation_prompt=task, object=object)
        
        Main.logger().info(f"\n\n Final Summarization Prompt is {final_prompt}")
        # Main.logger().info(f"Final prompt in summariser {final_prompt}")
        tokens = await self.llm.token_counter(str(final_prompt))
        response = 'Cannot process the response right now as it contains too many tokens !'

        if tokens < 128000:
            response = await self.llm_summerizer.acompletion(final_prompt, stream_response, role=role, max_tokens = 4096)

        else:
            Main.logger().debug(response)
        Main.logger().info(f"The response from summarization is {response}")
        
        #self.llm = self.llm_manager.get_service(llm_provider =  LLMProvider.openai.value, model_name = "gpt-4-turbo")
        return response
    

    async def endpoint_generator(self, search_result: str, question: str, context: any,generated_endpoints: list, role:str):
        """Generates an endpoint given an OpenAPI spec and a user question"""
        prompt = self.prompts.prompt("generator").get("text")
        final_prompt = prompt.format(question=question, open_api_spec=search_result, context=context, previous_generations=generated_endpoints, response_schema = self.api_generator_schema)
        #Main.logger().info(f"\n\n **** API generator Prompt is {final_prompt} ***** \n\n")
        response = await self.llm.completion(final_prompt, role=role)
        return response
    
    @timeit
    async def retry_generator_using_response(self,search_result: list[dict], task:str, task_context: str, role: str):
        generated_endpoints = []
        response, endpoint_urls = None, None

        # TODO:loop over generated endpoint & retry for each of them if fails in case of multiple endpoints
        GENERATOR_MAX_RETRIES = Main.configuration().common_configuration.max_retries
        for retry in range(GENERATOR_MAX_RETRIES):
            generated_endpoint = await self.endpoint_generator(search_result, task, task_context,generated_endpoints, role)
            Main.logger().info(f"Generated Endpoint is {generated_endpoint}")
            # generated_endpoint = ast.literal_eval(generated_endpoint)
            try:
                generated_endpoint = json.loads(generated_endpoint)
            except json.JSONDecodeError as e:
                Main.logger().info("Generated Endpoint was not a valid json object, retrying..")
                continue

            if not isinstance(generated_endpoint, list):
                generated_endpoint = [generated_endpoint]
             
            # Execute API against generated endpoint
            response, endpoint_urls = await self.api_handler.executer(generated_endpoint)

            if 'error' not in str(response).lower() and (list(response[0].values()))[0]:
                return response, endpoint_urls

            if len(generated_endpoint) == 1:
                # TODO Reflection prompt - add to prompts.py and let LLM correct API endpoints
                reflection ="\n\n **** Do reflect on the parameters and their descriptions and pay very close attention to what is mentioned there. Reflect deeply onto those and check if you violated any of those rules which resulted in this error. MAKE SURE TO TRY SOME VARIATIONS IN THE API PARAMETERS ****"
                # Only add reflection prompt when the API response is not correct the first time.
                generated_endpoints.append((str(generated_endpoint)) + " resulted in error as " + str(response) + "\n" + reflection)
            Main.logger().info(f"Retrying({retry}) generating endpoint with..\n")
            
        return response, endpoint_urls

    @timeit
    # @asyncify
    async def execute_tasks(self, tasks_json: str, query_context: QueryContext, step_functions) :
        """Executes individual tasks one-by-one. The tasks could be either API executor or clarifier or transformer or error handler"""
        # Parse the JSON string to a dictionary
        tasks_dict = json.loads(tasks_json)
        # Access the 'plan' key from the dictionary  
        tasks = tasks_dict.get('plan', '')
        
        Main.logger().debug("Task received by execute_tasks: %s", tasks)
        search_information = ""
        response, previous_task_context, task_responses =  " ", [],[]
        stream_response = query_context.stream_response
        role = query_context.role

        # Splitting the string into multiple tasks by using \n separator
        split_tasks = tasks.split('\n')

        Main.logger().debug(f"# of tasks {len(split_tasks)}")
        await step_functions.get('planner')(f"I've made a plan with {len(split_tasks)} steps. It will take me approximately {len(split_tasks)*18} seconds to answer your question. Here's the plan: \n\n {tasks}",)
        COLLECTION_NAME="AGENT_RESPONSE"
        # task_responses.append(query_context.conversation_context)
        for index, task in enumerate(split_tasks):
            await stream_response(f"\n\n - Executing task # {index+1} \n")
            
            if '[API]' in task:
                await step_functions.get('api')("Fetching data via API")
                # Search for the OpenAPI spec to gather relevant info for the llm
                search_result = await self.search_manager.search(task, "OpenAPISpecs")
                Main.logger().info(f"VectorDB Search Result is ... {search_result}")
                
                # Gather relevant context from previous task if there are more than one API task
                if index > 0:
                    previous_task_context = task_responses[index - 1]

                # Generate an endpoint with the OpenAPI spec + task
                response, endpoint_urls = await self.retry_generator_using_response(search_result, task, task_context=previous_task_context, role=role)
                
                try:
                    if len(endpoint_urls) > 0:
                        await stream_response(f"\n ## Executed {len(endpoint_urls)} with response size of {len(str(response))//4} tokens")
                except BaseException as e:
                        Main.logger().info(f" API Generator failed with exception {e}")
                        response = []
                        endpoint_urls = ["/apiurl"]
                        response.append({"/apiurl":"No API response received"})

                Main.logger().info(f"Endpoint urls are ... {endpoint_urls}")

                Main.logger().info(f"Execution api_response : {(str(response))[:400]}")
                Main.logger().info(f"Endpoint URL           : {(str(endpoint_urls))[:400]}")

                if response[0][endpoint_urls[0]]:
                    task_responses.append(response)

            elif '[Search]' in task:
                Main.logger().info("Entered global search Task")
                await step_functions.get('search')(f"Searching the internet with the Search agent")
                if index>0:
                    #Only add search information if there is a previous response
                    
                    search_information = str(task_responses[index - 1])
                    search_information = search_information[:10000]
                    
                
                response =  await self.global_search(task=task,role=role, search_information = search_information)
                await step_functions.get('search')(f"Results from the Search agent. \n\n query:\n {task} \n\n Response: \n{response}")
                task_responses.append(response)

            elif '[Summarization]' in task:
                # This assumes that every Summarization is always followed by an Aggregation task
                Main.logger().info("Entered Summarization Task")
                Main.logger().info(f"Role received from user: {role}")
                Main.logger().info(f"All task responses : {task_responses}")
                persona_task = f"You are creating response for a user with {role} privileges. Now do " + task
                #response = await self.summarizer(query_context.conversation_context.json(), persona_task, stream_response, role=role)
                
                # Accessing previous task response from task response list. This will ensure both mongoDB agent + direct response to be accessed
                # response = await self.summarizer(task_responses[index - 1], persona_task, stream_response, role=role)
                
                
                # TODO: Global search will need all tasks for perplexity
                response = await self.summarizer(task_responses, persona_task, stream_response, role=role)

                if response:
                    query_context.conversation_context.save_context({"inputs": task}, {"outputs": response})
                    task_responses.append(response)
                Main.logger().info(f"\n\n***** Updated Context after summarization {query_context} \n\n")
           
            elif '[Clarification]'.lower() in task.lower():

                Main.logger().info("Entered Clarification task")
                await step_functions.get('clarification')("I need to get clarification before I go ahead...",)
                response = task
            
            else:
                Main.logger().debug("Unidentified Task")

        return response
