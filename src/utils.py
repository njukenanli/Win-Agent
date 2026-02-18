import os
import time
from src.runtime import Runtime


class Utils:
    @staticmethod
    def reset_cwd(container: Runtime) -> None: 
        goto_cwd = r"cd C:\testbed  " if container.platform == "windows" else "cd /testbed  "
        container.send_command(goto_cwd)
    
    @staticmethod
    def safe_read(path: str) -> str:
        '''
        write file ops from the host need time to sync to container.
        '''
        for trial in range(3):
            try:
                time.sleep(16)
                with open(os.path.abspath(path), encoding="utf-8") as f:
                    s = f.read()
                    return s
            except:
                continue
        raise FileNotFoundError(path)