"""Store for API functions"""


class ApiFunctionStore:
    """Store for API functions"""

    _FUNCTIONS = [
        {
            "name": "get_current_weather",
            "description": "Get the current weather in a given location",
            "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "The city and state, e.g. San Francisco, CA"
                        },
                        "unit": {
                            "type": "string",
                            "enum": [
                                "celsius",
                                "fahrenheit"
                            ]
                        }
                    },
                "required": [
                        "location"
                ]
            }
        },
        {
            "name": "get_airports",
            "description": "Query all airports",
            "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "The city and state, e.g. San Francisco, CA"
                        },
                        "unit": {
                            "type": "string",
                            "enum": [
                                "celsius",
                                "fahrenheit"
                            ]
                        }
                    },
                "required": [
                        "location"
                ]
            }
        }
    ]

    @staticmethod
    def functions() -> dict:
        """Returns the list of functions"""
        return ApiFunctionStore._FUNCTIONS
