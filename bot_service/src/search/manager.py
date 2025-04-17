from common.service_management import ServiceManager
from LLM.manager import LLMServiceManager
from langchain.document_loaders.csv_loader import CSVLoader
from common.base import Main
import os
import json
import traceback
from langchain.docstore.document import Document
import asyncify
import chromadb
import uuid
import hashlib


class SearchServiceManager(ServiceManager):

    def __init__(self, _llm_service_manager: LLMServiceManager):
        super().__init__()
        self._database_directory = Main.configuration(
        ).vectorDB_configuration.database_directory
        self.llm = _llm_service_manager.openai_service()


        #Uncomment if you want to try with OpenAI instead of Azure OpenAI
        # self.llm = _llm_service_manager.openai_service()
        self._database = None

        self.embedding_function = None

    async def prepare(self) -> None:
        """Prepares the service manager"""
        self.embedding_function =  await self.llm.get_embeddings(chunk_size=16)
        await self.setup_search_database_if_not_exists()

    async def calculate_checksum(self, docs_to_embed: list[str]):
        BUF_SIZE = 65536
        hash = hashlib.sha1()
        for file in docs_to_embed:
            try:
                with open(file, 'rb') as f:
                    while True:
                        data = f.read(BUF_SIZE)
                        if not data:
                            break
                        hash.update(data)
                #hash.update(Path(file).read())
            except IsADirectoryError:
                pass
        return hash.hexdigest()
    
    async def update_checksum(self, to_embed, json_path: str):
        collection_names = []
        collection_dict = {}
        for embed_object in to_embed:
            collection_names.append(embed_object.get("name"))
            collection_dict[embed_object.get("name")] = []
            
        for embed_object in to_embed:
            collection_dict[embed_object.get("name")] += [embed_object.get("location")]
        collection_names = set(collection_names)
        update_flag = [False] * len(collection_names)

        for iter, name in enumerate(collection_names):
            file_hash = await self.calculate_checksum(collection_dict[name])

            for embed_object in to_embed:
                if (name==embed_object.get("name")):
                    if(file_hash != embed_object.get("sha1sum")):
                        embed_object["sha1sum"] = file_hash
                        update_flag[iter] = True
            
            
        
        write_embeddings = json.dumps(to_embed, indent=4)
        with open(json_path, "w", encoding="utf-8") as outfile:
            outfile.write(write_embeddings)
        return update_flag
        
    

    async def add_data_to_chroma(self, doc: Document, collection_name: str):
        collection = self._database.get_or_create_collection(name=collection_name)
        ids=[str(uuid.uuid5(uuid.NAMESPACE_DNS, txt.page_content)) for txt in doc]
        metadatas = [txt.metadata for txt in doc]
        documents = [txt.page_content for txt in doc]
        embeddings = [self.embedding_function.embed_query(txt.page_content) for txt in doc]
        collection.upsert(ids=ids, metadatas=metadatas, documents=documents, embeddings=embeddings)
        
        

    @asyncify
    def search(self, query: str, collection_name: str) -> list[dict]:
        """Searches for API functions based on the given query, it must return the OpenAI function definitions"""
        # TO DO : Change search result to param
        # results = self._database.similarity_search_with_score(query, k=1) 
        results = self._database.get_collection(collection_name).query(query_embeddings=self.embedding_function.embed_query(query), n_results=1)

        results = results['documents']
        
        return [results]

    async def setup_search_database_if_not_exists(self) -> None:
        """Sets up the search database if it does not exist"""
        try:
            if not os.path.exists(self._database_directory):
                Main.logger().info('Embedding directory not found...creating it now')
                # os.makedirs(self._database_directory, exist_ok=True)
                self._database = chromadb.PersistentClient(path=self._database_directory)
                await self.generate_embeddings(False)
            else:
                self._database = chromadb.PersistentClient(path=self._database_directory)
                await self.generate_embeddings(True)      

        except OSError as e:
            Main.logger().debug(
                f"Could not create directory {self._database_directory}: {e}", exc_info=1)
            # handle error as appropriate for your application

    async def split_json_into_chunks(self,json_content):
        chunks = []
        components = json_content.get('components', {})
        paths = json_content.get('paths', {})

        for path, methods in paths.items():
            path_details = [f"Path: {path}"]

            for method, details in methods.items():
                path_details.append(f"Method: {method.upper()}")
                path_details.append(f"Summary: {details.get('summary', 'Summary N/A')}")
                path_details.append(f"Description: {details.get('description', 'Description N/A')}")

                # Include parameters directly associated with the method
                for param in details.get('parameters', []):
                    param_str = f"Parameter: {param['name']} - {param.get('description', 'No description')}"
                    path_details.append(param_str)

                # Look up and include relevant schema from components if referenced
                if 'requestBody' in details and 'content' in details['requestBody']:
                    schema_ref = details['requestBody']['content']['application/json'].get('schema', {}).get('$ref', '')
                    schema_key = schema_ref.split('/')[-1]  # Assumes ref format like "#/components/schemas/inputSchema"
                    if schema_key in components['schemas']:
                        schema_details = components['schemas'][schema_key]
                        path_details.append(f"Schema: {schema_key} - {json.dumps(schema_details, indent=2)}")

                # Responses and other method details
                for status, response in details.get('responses', {}).items():
                    response_str = f"Response: {status} - {response.get('description', 'No description')}"
                    path_details.append(response_str)

            chunks.append('\n'.join(path_details))

        return chunks

    async def generate_embeddings(self, is_directory_exists: bool):
        try:
            Main.logger().info(f"Generating embeddings...")

            json_path = Main.configuration().vectorDB_configuration.embeddings_json_file

            with open(json_path, "r") as file:
                to_embed = json.load(file)

            update_flag = await self.update_checksum(to_embed, json_path)

            collection_names = set([embed_object.get("name") for embed_object in to_embed])

            update_dict = {}

            for iter, name in enumerate(collection_names):
                update_dict[name] = update_flag[iter]
                if(update_flag[iter]==True):
                    try:
                        self._database.delete_collection(name)
                    except ValueError:
                        Main.logger().debug(f"The collection ... {name} does not exist. It will be created.")

            

            for embed_object in to_embed: 
                match embed_object.get("file_type"):
                    case "json":
                        if(update_dict[embed_object.get("name")]==True or is_directory_exists==False):
                            with open(embed_object.get("location"), 'r') as file:
                                json_content = json.load(file)
                            chunks = await self.split_json_into_chunks(json_content)
                            # Main.logger().info(f"Chunks being split into 1 {chunks[0]}")
                            documents = [Document(page_content=json.dumps(json_content), metadata={"chunk_number": i+1}) for i, chunk in enumerate(chunks)]
                            await self.add_data_to_chroma(documents, embed_object.get("name"))
                        
                    case "csv":
                        if(update_dict[embed_object.get("name")]==True or is_directory_exists==False):
                            knowledgebase = CSVLoader(embed_object.get("location")).load()
                            await self.add_data_to_chroma(knowledgebase, embed_object.get("name"))

                    case _:
                        raise ValueError("Please provide a valid filetype")
            

        except Exception as e:
            tracer = traceback.format_exc()
            Main.logger().debug(f'Some error occurred in embeddings...{tracer}')
