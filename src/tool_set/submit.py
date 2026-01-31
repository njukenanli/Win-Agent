from src.runtime import Runtime
from src.tool_set.base import Tool
from typing import Any

class Submit(Tool):
    tool = {
            "type": "function",
            "function": {
                "name": "submit",
                "description": "submit your edits (or give up) and exit.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        }
    
    @staticmethod
    def tool_call(container: Runtime, args: dict[str, Any]) -> str:
        pass