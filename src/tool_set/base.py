from abc import ABC, abstractmethod
import os
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
    def temp_file(mnt_host: str, mnt_container: str) -> tuple[str, str]:
        '''
        returns: 
        host_path, container_path
        '''
        uidx = uuid.uuid4()
        return os.path.join(mnt_host, f"{uidx}.txt"), os.path.join(mnt_container, f"{uidx}.txt")
    
    @staticmethod
    def safe_read(path: str) -> str:
        return Utils.safe_read(path)