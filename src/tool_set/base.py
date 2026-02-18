from abc import ABC, abstractmethod
import os
import time
from typing import Any
from src.runtime import Runtime
from src.utils import Utils
import uuid

class Tool(ABC):
    tool: dict[str, Any]

    @staticmethod
    @abstractmethod
    def tool_call(container: Runtime, args: dict[str, Any]) -> str:
        pass

    @staticmethod
    def reset_cwd(container: Runtime) -> None: 
        Utils.reset_cwd(container)
    
    @staticmethod
    def temp_file() -> str:
        return f"mnt/{uuid.uuid4()}.txt"
    
    @staticmethod
    def safe_read(path: str) -> str:
        return Utils.safe_read(path)