import time

from src.runtime import Runtime
from src.tool_set.base import Tool
from typing import Any


class Create(Tool):
    tool = {
            "type": "function",
            "function": {
                "name": "create",
                "description": "create a new file at `path`, overwrite content `content` into the file.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string"
                        },
                        "content": {
                            "type": "string"
                        }
                    },
                    "required": ["path", "content"]
                }
            }
        }
    
    @staticmethod
    def tool_call(container: Runtime, args: dict[str, Any]) -> str:
        path = args.get("path", None)
        if path is None:
            return "parameter `path` is required for create tool call"
        path = path.strip('"').strip("'").strip("`")
        content = args.get("content", None)
        if content is None:
            return "parameter `content` is required for create tool call"
        Tool.reset_cwd(container)
        test_dir = f'if (Test-Path "{path}" -PathType Container) {{}} else {{throw}}' if container.platform == "windows" else f'[ -d "{path}" ]'
        res = container.send_command(test_dir)
        if res.metadata.exit_code == 0:
            return f"Path {path} is directory. Cannot overwrite file content on directory."
        temp_file_host, temp_file_container = Tool.temp_file(container.mnt_host, container.mnt_container)
        with open(temp_file_host, "w", encoding = "utf-8") as f:
            f.write(content)
        time.sleep(16) # wait for file to sync to container
        clean_cmd = f"Remove-Item '{path}' -Force -ErrorAction SilentlyContinue" if container.platform == "windows" else f"rm -f '{path}'"
        container.send_command(clean_cmd)
        res = container.send_command(f"mv '{temp_file_container}' '{path}' ")
        clean_cmd = f"Remove-Item '{temp_file_container}' -Force -ErrorAction SilentlyContinue" if container.platform == "windows" else f"rm -f '{temp_file_container}'"
        container.send_command(clean_cmd)
        if res.metadata.exit_code == 0:
            return "file created successfully."
        else:
            return res.output
