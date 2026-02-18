import os
import time
from src.runtime import Runtime


class Utils:
    @staticmethod
    def reset_cwd(container: Runtime) -> None: 
        goto_cwd = r"cd C:\testbed  " if container.platform == "windows" else "cd /testbed  "
        container.send_command(goto_cwd)
    
    @staticmethod
    def read_with_encoding_problem(path: str) -> str:
        for encoding in ["utf-8", "utf-16", "utf-16-le", "utf-16-be", "latin-1"]:
            try:
                with open(path, encoding=encoding) as f:
                    s = f.read()
                return s
            except (UnicodeDecodeError, UnicodeError):
                pass
        else:
            with open(path, encoding="utf-8", errors="ignore") as f:
                s = f.read()
            return s

    @staticmethod
    def safe_read(path: str) -> str:
        '''
        write file ops from the host need time to sync to container.
        '''
        path = os.path.abspath(path)
        for trial in range(3):
            try:
                time.sleep(16)
                s = Utils.read_with_encoding_problem(path)
                return s
            except:
                continue
        raise FileNotFoundError(path)