import os
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
        
        path_file_host, path_file_container = Tool.temp_file(container.mnt_host, container.mnt_container)
        with open(path_file_host, "w", encoding = "utf-8") as f:
            f.write(path)
        old_file_host, old_file_container = Tool.temp_file(container.mnt_host, container.mnt_container)
        with open(old_file_host, "w", encoding = "utf-8") as f:
            f.write(old_string)
        new_file_host, new_file_container = Tool.temp_file(container.mnt_host, container.mnt_container)
        with open(new_file_host, "w", encoding = "utf-8") as f:
            f.write(new_string)
        time.sleep(16) # allow time for file write op sync between host and container.
        output_file_host, output_file_container = Tool.temp_file(container.mnt_host, container.mnt_container)
        Tool.reset_cwd(container)
        
        src_code_file = os.path.join(container.mnt_container, "replace.py")
        command = f"python {src_code_file} --path_file {path_file_container} --old_file {old_file_container} --new_file {new_file_container} --output_file {output_file_container}"
        container.send_command(command)
        res = Tool.safe_read(output_file_host)
        container.send_command(f"rm {path_file_container} ; rm {old_file_container} ; rm {new_file_container} ; rm {output_file_container}")
        return res
