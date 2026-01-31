from src.runtime import Runtime
from src.tool_set.base import Tool
from typing import Any

class Shell(Tool):
    tool = {
            "type": "function",
            "function": {
                "name": "shell",
                "description": "run a powershell command.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": "Powershell command to run"
                        }
                    },
                    "required": ["command"]
                }
            }
        }
    @staticmethod
    def tool_call(container: Runtime, args: dict[str, Any]) -> str:
        command = args.get("command", None)
        if command is None:
            return "The command parameter of the tool call shell is required."
        res = container.send_command(command, 60*60)
        return res.to_observation()
    
