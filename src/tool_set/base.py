from abc import ABC, abstractmethod
from typing import Any
from src.runtime import Runtime
import uuid

class Tool(ABC):
    tool: dict[str, Any]

    @staticmethod
    @abstractmethod
    def tool_call(container: Runtime, args: dict[str, Any]) -> str:
        pass

    @staticmethod
    def reset_cwd(container: Runtime) -> None: 
        goto_cwd = r"cd C:\testbed  " if container.platform == "windows" else "cd /testbed  "
        container.send_command(goto_cwd)
    
    @staticmethod
    def temp_file() -> str:
        return f"mnt/{uuid.uuid4()}.txt"