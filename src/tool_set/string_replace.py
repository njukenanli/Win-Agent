import time
from src.runtime import Runtime
from src.tool_set.base import Tool
from typing import Any


class Replace(Tool):
    tool = {
            "type": "function",
            "function": {
                "name": "string_replace",
                "description": "replace sub-string old_string with new_string in the file at `path`",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string"
                        },
                        "old_string": {
                            "type": "string"
                        },
                        "new_string": {
                            "type": "string"
                        }
                    },
                    "required": ["path", "old_string", "new_string"]
                }
            }
        }
    
    @staticmethod
    def tool_call(container: Runtime, args: dict[str, Any]) -> str:
        path = args.get("path", None)
        if path is None:
            return "parameter `path` is required for string_replace tool call"
        path = path.strip('"').strip("'").strip("`")
        old_string = args.get("old_string", None)
        if old_string is None:
            return "parameter `old_string` is required for string_replace tool call"
        new_string = args.get("new_string", None)
        if new_string is None:
            return "parameter `new_string` is required for string_replace tool call"
        
        path_file = Tool.temp_file()
        with open(path_file, "w", encoding = "utf-8") as f:
            f.write(path)
        old_file = Tool.temp_file()
        with open(old_file, "w", encoding = "utf-8") as f:
            f.write(old_string)
        new_file = Tool.temp_file()
        with open(new_file, "w", encoding = "utf-8") as f:
            f.write(new_string)
        time.sleep(16) # allow time for file write op sync between host and container.
        output_file = Tool.temp_file()
        Tool.reset_cwd(container)
        
        command = f"python -m mnt.replace --path_file {path_file} --old_file {old_file} --new_file {new_file} --output_file {output_file}"
        container.send_command(command)
        time.sleep(16) # allow time for file write op sync between host and container.
        with open(output_file, encoding = "utf-8") as f:
            res = f.read()
        container.send_command(f"rm {path_file} ; rm {old_file} ; rm {new_file} ; rm {output_file}")
        return res
