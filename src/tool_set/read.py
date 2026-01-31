import time
from src.runtime import Runtime
from src.tool_set.base import Tool
from typing import Any


class Read(Tool):
    tool = {
            "type": "function",
            "function": {
                "name": "read",
                "description": "read file at `path` from line number `start` to `end`. if start and end are not provided, the whole file content is returned.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string"
                        },
                        "start": {
                            "type": "integer"
                        },
                        "end": {
                            "type": "integer"
                        }
                    },
                    "required": ["path"]
                }
            }
        }
    
    @staticmethod
    def tool_call(container: Runtime, args: dict[str, Any]) -> str:
        path = args.get("path", None)
        if path is None:
            return "parameter `path` is required for read tool call"
        start = args.get("start", None)
        end = args.get("end", None)
        extra_cmd = ""
        if (start is not None) and (end is not None):
            if start < 0:
                return "start line number should be >= 0"
            if start > end:
                return "start line number should be < end line number"
            extra_cmd = f"--start {start} --end {end}"
        path_file = Tool.temp_file()
        with open(path_file, "w", encoding = "utf-8") as f:
            f.write(path)
        time.sleep(16) # allow time for file write op sync between host and container.
        output_file = Tool.temp_file()
        Tool.reset_cwd(container)
        command = f"python -m mnt.read --path_file {path_file} --output_file {output_file}  {extra_cmd}"
        container.send_command(command)
        time.sleep(16) # allow time for file write op sync between host and container.
        with open(output_file, encoding = "utf-8") as f:
            res = f.read()
        container.send_command(f"rm {path_file} ; rm {output_file}")
        return res
