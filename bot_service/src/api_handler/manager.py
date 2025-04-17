from common.service_management import ServiceManager
from common.base import Main
from pathlib import Path

import json
import requests
import traceback

from apify_client import ApifyClient
import aiohttp


class APIHandlerServiceManager(ServiceManager):

    def __init__(self) -> None:
        super().__init__()
        self.actor = None
        self._schemas = list()
        self._access_token = None

    
    async def prepare(self):
        openapi_spec_dir = Main.configuration().api_handler_configuration.openapi_spec_dir
        openapi_files = Path(openapi_spec_dir).glob("**/*")
        for openapi_file in openapi_files:
            if openapi_file.suffix.endswith("json"):
                with open(openapi_file, 'r') as f:
                    self._schemas.append(json.load(f))

        self._access_token = await self.get_api_access_token()

        # TODO: Can be a list ? but it is not feasible to run all actors/scrapers, runs only the Similar web scraper actor and wait for it to finish
        self.actor = Main.configuration().api_handler_configuration.actor_name

    
    async def get_required_optional_spec_param(self,spec_params: list) -> (list, list):
        required_spec_params, optional_spec_params = [],[]   
        for param in spec_params:
            param_required = param.get('required')
            
            if param_required:
                required_spec_params.append(param.get('name'))
            
            elif param_required is not None:
                optional_spec_params.append(param.get('name'))
        
        return (required_spec_params,optional_spec_params)
    

    async def validate_required_param(self, required_params_from_spec: list, endpoint_params: list) -> list:
        messages = []         
        if not required_params_from_spec:
            Main.logger().info(f'Required param validation success as there were none in spec.')
            return messages
            
        for required_param in required_params_from_spec:
            if required_param in endpoint_params:
                Main.logger().info(f'Required param "{required_param}" validation success.')
            else:
                messages.append(f'Required param "{required_param}" was not found in "{required_params_from_spec}", please try again')
        
        return messages
    

    async def validate_optional_param(self, optional_params_from_spec: list, optional_params_from_endpoint: list) -> list :
        
        messages = []
        for param in optional_params_from_endpoint :
            if param in optional_params_from_spec:
                Main.logger().info(f'Optional param "{param}" vaidation sucess')
            else:
                messages.append(f'Optional param "{param}" was not found in "{optional_params_from_spec}" is invalid, please try again')
                
        return messages
    

    async def validate_endpoints(self,endpoints: list[dict]) -> list[dict]:
        try:      
            paths = self._schemas.get("paths")
            validations = []
            
            for endpoint in endpoints:
                if endpoint.get('url') and endpoint.get('method'):
                    
                    endpoint_url = endpoint.get("url")
                    endpoint_method = endpoint.get("method").lower()
                    endpoint_params = endpoint.get("data",[])
                    
                    temp_dict = {endpoint_url : []}

                    # check if endpoint url exists
                    if paths.get(endpoint_url) :
                        Main.logger().info(f'URL validation success for "{endpoint_url}".')
                    else:
                        temp_dict[endpoint_url].append(f'"{endpoint_url}" is not valid, please try again') 
                    
                    # check if the http method exists
                    if paths.get(endpoint_url) and paths.get(endpoint_url).get(endpoint_method):
                        endpoint_method = endpoint.get("method").lower()
                        Main.logger().info(f'HTTP method validation success for "{endpoint_method}".')
                    else:
                        temp_dict[endpoint_url].append(f'"{endpoint_method}" is not valid, please try again')

                    # check if required parameters exists
                    # here the spec contains the *required* key in parameters 
                    spec_params = paths.get(endpoint_url, {}).get(endpoint_method, {}).get("parameters")
                            
                    if spec_params:
                        required_spec_params, optional_spec_params = await self.get_required_optional_spec_param(spec_params)
                            
                        # remove required from endpoints if any, send remaining params as optional which not required params
                        optional_params_from_endpoint = [value for value in endpoint_params if value not in required_spec_params]
                        
                        # check required & optional params from from api_spec, append error there any missing or can be skipped          
                        temp_dict[endpoint_url].extend(await self.validate_required_param(required_spec_params, endpoint_params))
                        temp_dict[endpoint_url].extend(await self.validate_optional_param(optional_spec_params, optional_params_from_endpoint))           
                    
                    elif endpoint_params:
                        temp_dict[endpoint_url].append(f'Params "{endpoint_params}" are not valid not found in open api spec, please try again')
                    else:
                        Main.logger().info(f'Zero optional param validation success for "{endpoint_url}".')
                    
                    validations.append(temp_dict)
                else:
                    raise KeyError(f'URL & HTTP Method was not found in the endpoint: {endpoint}')             
                
            return validations
                
        except Exception as e:
            Main.logger().info(f'Skipping validation for "{endpoint}" as {traceback.format_exc()}')   
        
    async def get_api_access_token(self) -> str:

        try:
            # not available in openapi spec
            token = Main.configuration().api_handler_configuration.token
            return token
        
        except (KeyError, json.JSONDecodeError) as e:
            Main.logger().debug(f'Could not generate access token..{e}',)
            return None
    
    
    # async def executer(self, run_input: dict) -> list[dict]:
        
    #     try:
    #         list_of_responses = [ ]
    #         if self._access_token is None:
    #             Main.logger().info('Access token was not found')
    #             return
            
    #         # Initialize the ApifyClient with your API token
    #         client = ApifyClient(str(self._access_token))

    #         # Prepare the Actor input
    #         run_input.setdefault("proxy",{ "useApifyProxy": True })

    #         # TODO:  Runs only the Similar web scraper actor and wait for it to finish
    #         run = client.actor(self.actor).call(run_input=run_input)

    #         # Fetch and print Actor results from the run's dataset (if there are any)
    #         for item in client.dataset(run["defaultDatasetId"]).iterate_items():
    #             list_of_responses.apppend(item)
            
    #         return list_of_responses

    #     except BaseException as e:
    #         Main.logger().debug(f'Something went unexpected while calling the API.. {e}..{traceback.format_exc()}',exc_info=1)

    async def executer(self,endpoints: list[dict]) -> list[dict]:
        
        try:
            if self._access_token is None:
                Main.logger().debug('Access token was not found')
                return
            
            list_of_responses, list_of_endpoint_urls = [], []
            headers = {
                'Content-Type': 'application/json'
            }

            response_text, response_json = None, None
            for endpoint in endpoints:

                http_method, endpoint_url = endpoint.get('method'), endpoint.get('url')
                endpoint_params, payload, server = endpoint.get('data') , {}, None


                # check if path exists
                for schema in self._schemas:
                    paths = schema.get("paths")
                    if paths.get(endpoint_url):
                        servers = schema.get('servers')
                        server = servers[0].get('url') if servers else None

                # if not server:
                #     list_of_responses.append({endpoint_url: "No server found for the endpoint"})
                #     continue

                # server_url = server
                server_url = "https://api.apify.com/v2"

                # if data dict/params are present, build the payload
                if endpoint_params:
                    for param in endpoint_params.keys():
                        lookout_param = '{' + param + '}'
                        if lookout_param in endpoint_url:
                            # replace required param with actual value of the param
                            endpoint_url = endpoint_url.replace(f"{{{param}}}",str(endpoint_params.get(param)))
                        else:
                            # all params can be sent as payload if recevied properly
                            # add it as optional param if it not endpoint/required key
                            payload[param] = endpoint_params.get(param)

                list_of_endpoint_urls.append(endpoint_url)
                # payload.setdefault('token',self._access_token)
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(600)) as session:
                    async with session.request(method=http_method, url=endpoint_url, 
                                               params={"token":self._access_token},
                                               json=payload,headers=headers)as response:
                        response_text = await response.text()
                        response_json = await response.json()
                # response = requests.request(http_method,url=endpoint_url, params={"token":self._access_token},json=payload,headers=headers)

                Main.logger().info(f"Response from API execution :  {(str(response_text))[:200]} , writing to file..")
                       
                Main.logger().info(f'Built payload : {payload}')
                Main.logger().info(f'Built url     : {server_url+endpoint_url}')

                # if access token is expired or something was invalid regenerate access token 
                # this will ensure token is regenerated only after expiration
                # if response.status_code == 401:
                #     Main.logger().info('Regenerating access token..')
                #     self._access_token = await self.get_api_access_token()
                #     headers = {'Authorization': f'Bearer {self._access_token}'}
                #     response = requests.request(http_method,url=server_url+endpoint_url,headers=headers,params=payload)

                if response.ok:
                    try:
                        list_of_responses.append({endpoint_url: response_json})
                    except json.JSONDecodeError as e:
                        Main.logger().debug(f'Could not parse json for endpoint with url : "{endpoint_url}"',exc_info=1)
                        list_of_responses.append({endpoint_url:'Parsing json failed !'})
                else:
                    # handle response based on content-type header
                    # response.text automatically guesses the encoding from header, for 404 the text may be empty
                    list_of_responses.append({endpoint_url:response_text})
            return list_of_responses, list_of_endpoint_urls

        except BaseException as e:
            Main.logger().debug(f'Something went unexpected while calling the API.. {e}..{traceback.format_exc()}',exc_info=1)