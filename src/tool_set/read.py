import os
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
        path_file_host, path_file_container = Tool.temp_file(container.mnt_host, container.mnt_container)
        with open(path_file_host, "w", encoding = "utf-8") as f:
            f.write(path)
        time.sleep(16) # allow time for file write op sync between host and container.
        output_file_host, output_file_container = Tool.temp_file(container.mnt_host, container.mnt_container)
        Tool.reset_cwd(container)
        src_code_file = os.path.join(container.mnt_container, "read.py")
        command = f"python {src_code_file} --path_file {path_file_container} --output_file {output_file_container}  {extra_cmd}"
        container.send_command(command)
        res = Tool.safe_read(output_file_host)
        container.send_command(f"rm {path_file_container} ; rm {output_file_container}")
        return res
