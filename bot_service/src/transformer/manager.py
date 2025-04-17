from common.service_management import ServiceManager, Service
from common.base import Main
from pathlib import Path
import json
from datetime import datetime

class TransformerServiceManager(ServiceManager):

    def __init__(self):
        super().__init__()
        self._filter_keys_dir = Main.configuration().transformer_configuration.filter_keys_dir

    @staticmethod
    def filter_keys(input_data, keys):
        """
        Filters a single dictionary or a list of dictionaries to only include specified keys.
        Keys can include nested structures represented by dot notation.

        :param input_data: A single dictionary or a list of dictionaries.
        :param keys: A list of keys that may include dot notation for nested structures.
        :return: The filtered dictionary or list of dictionaries.
        """
        def parse_key_path(key):
            """
            Parses a dot notation key into a list of keys and indices.
            """
            parts = key.split('.')
            parsed = []
            for part in parts:
                if '[]' in part:
                    name, _ = part.split('[]')
                    parsed.append(name)
                    parsed.append('[]')  # Special marker for arrays
                else:
                    parsed.append(part)
            return parsed

        def filter_dict(d, key_paths):
            """
            Recursively filters a dictionary based on the provided key paths.
            """
            # print(f"\n\n\n Key paths are {key_paths}")
            # print(f"\n\n\n d is {d}")
            if not isinstance(d, dict):
                return d

            filtered = {}
            for key_path in key_paths:
                current = d
                try:
                    for i, part in enumerate(key_path):
                        if part == '[]':
                            # Handle array
                            if isinstance(current, list):
                                current = [filter_dict(item, [key_path[i+1:]]) for item in current]
                                break
                        else:
                            # print(f"\n\n\n Current type is {type(current)}")
                            # print(f"\n\n\n Current is {current} ")
                            current = current[part]
                    else:
                        # Successfully navigated the key path, include this value
                        nested_set(filtered, key_path, current)
                except KeyError:
                    pass  # Key path not present in the dictionary
            return filtered

        def nested_set(dic, keys, value):
            """
            Sets a value in a nested dictionary based on a list of keys.
            """
            for key in keys[:-1]:
                dic = dic.setdefault(key, {})
            dic[keys[-1]] = value

        # Convert all keys to parsed key paths
        key_paths = [parse_key_path(key) for key in keys]

        # Ensure input_data is a list for uniform processing
        if isinstance(input_data, dict):
            input_data = [input_data]

        # Filter each dictionary in the list
        filtered_list = [filter_dict(item, key_paths) for item in input_data]

        # Return in the same format as the input
        return filtered_list

    def filter_parse(self, key, json_data):
        #TODO Read these from configuration file
        keys_ = '/api/'
        
        filter_keys_files = Path(self._filter_keys_dir).glob("**/*")
        for filter_keys_file in filter_keys_files:
            if filter_keys_file.suffix.endswith("json"):
                with open(filter_keys_file, 'r') as keys_file:
                    filter_keys_data = json.load(keys_file)
                    keys = filter_keys_data.get(keys_ , [])
                    if len(keys) > 1:
                        return TransformerServiceManager.filter_keys( json_data, keys)
        
    def filter_api_responses(self, endpoint_urls, response):
        filtered_responses = []
        for endpoint_url, single_response in zip(endpoint_urls, response):
            if len(response) ==0:
                Main.logger().debug("The API response returned no response")
                break
            filtered_response = self.filter_parse(endpoint_url, json_data=single_response.get(endpoint_url))
            filtered_responses.append({endpoint_url: filtered_response})

        try:
            filtered_documents = []
            for filtered_response in filtered_responses:
                for k, v in filtered_response.items():
                    filtered_documents.extend(v)
            Main.logger().info(f"type of data - {type(filtered_documents)} and length {len(filtered_documents)}")
        except:
            Main.logger().debug("Filter response failed")
        return filtered_documents, filtered_responses
    
if __name__ == "__main__":
    transformer = TransformerServiceManager()
    import json
    with open('sample.json', 'r') as json_file, open('./bagtags_keys.json', 'r') as keys_file:
        data = json.load(json_file)
        keys_data = json.load(keys_file)
        keys = keys_data.get('keys', [])
        print(f"The keys are {keys} and the type is {type(keys)}")
        filtered_data = transformer.filter_keys(data, keys)
        with open("filtered_data.json",'w') as f:
            json.dump(filtered_data,f)
