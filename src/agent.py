
from functools import partial
import json
import os
from datetime import datetime
import time
from typing import Any, Literal, Optional

from litellm import ChatCompletionMessageToolCall
from src.runtime import Runtime
from src.llm import LLM
from src.tools import Tools
from litellm.types.utils import ModelResponse, Message
import traceback

class Agent:
    def __init__(self, 
                 model: str, 
                 api_key: str, 
                 base_url: str|None,
                 tools: list[str], 
                 prompt: str, 
                 max_steps: int, 
                 platform: Literal["linux", "windows"],
                 run_id: str):
        self.tools = Tools(tools)
        self.llm = LLM(model, api_key, base_url, self.tools.tools)
        self.max_steps = max_steps
        self.prompt_template = prompt
        self.run_id = run_id
        self.platform = platform
        self.exit_status: dict[str, Literal["submitted", "exit_cost", "error"]] = {}

    def logger(self, instance_id: str, log: str):
        os.makedirs(f"output/{self.run_id}/logs", exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(f"output/{self.run_id}/logs/{instance_id}.txt", "a", encoding="utf-8") as f:
            f.write(f"\n[{timestamp}]: \n{log}\n")

    def install_py(self, container: Runtime):
        if container.platform=="windows":
            container.send_command("""
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {$u="https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe";$f="$env:TEMP\python-3.12.10-amd64.exe";Invoke-WebRequest $u -OutFile $f;Start-Process $f "/quiet InstallAllUsers=1 PrependPath=1 Include_test=0" -Wait;$env:Path+=";C:\Program Files\Python312"}
""")
        else:
            container.send_command("if ! command -v python >/dev/null; then sudo apt-get update && sudo apt-get install -y python3.12; fi")

    def init_git(self, container: Runtime):
        container.send_command("git config --global user.name localuser ; git config --global user.email localuser@example.com")
        if container.platform == "linux":
            container.send_command("git config --global --add safe.directory /testbed")
        elif container.platform == "windows":
            container.send_command(r"git config --global --add safe.directory C:\testbed")
            # Grant full permissions on C:\testbed to ensure all operations succeed
            container.send_command(r'icacls "C:\testbed" /grant "Everyone:(OI)(CI)F" /T /Q')
        container.send_command("git add --update ; git commit -m 'local changes' ")


    def set_mnt_permissions(self, container: Runtime) -> None:
        if container.platform == "windows":
            ps_script = r'''
$root = "C:\\testbed\\mnt"
if (Test-Path $root) {
  Get-ChildItem -Path $root -Recurse -File -ErrorAction SilentlyContinue | ForEach-Object {
    if ($_.Extension -ieq ".py") { $_.IsReadOnly = $true } else { $_.IsReadOnly = $false }
  }
}
'''
            container.send_command(ps_script)
        else:
            mnt_path = "/testbed/mnt"
            cmd = (
                f'if [ -d "{mnt_path}" ]; then '
                f'chmod -R a+rwX "{mnt_path}" && '
                f'find "{mnt_path}" -type f -name "*.py" -exec chmod a=r {{}} +; '
                f'fi'
            )
            container.send_command(cmd)

    
    def save_patch(self, container: Runtime, instance_id: str):
        goto_cwd = r"cd C:\testbed  " if container.platform == "windows" else "cd /testbed  "
        container.send_command(goto_cwd)
        os.makedirs(f"output/{self.run_id}/patch", exist_ok=True)

        temp_file = f"mnt/{self.run_id}_{instance_id}.diff"
        patch = container.send_command(f"git --no-pager diff HEAD --diff-filter=M --text > {temp_file}")
        time.sleep(16)
        for encoding in ["utf-8", "utf-16", "utf-16-le", "utf-16-be", "latin-1"]:
            try:
                with open(temp_file, encoding=encoding) as f:
                    patch = f.read()
                break
            except (UnicodeDecodeError, UnicodeError):
                pass
        else:
            with open(temp_file, encoding="utf-8", errors="ignore") as f:
                patch = f.read()
        patch = patch.replace("""PS>
PS>prompt""", "").replace("git --no-pager diff HEAD --diff-filter=M --text", "")
        start = patch.find("diff --git")
        patch = patch[start:]
        patch_file = f"output/{self.run_id}/patch/{instance_id}.diff"
        with open(patch_file, "w", encoding="utf-8") as f:
            f.write(patch)
        container.send_command(f"rm {temp_file}")
    
    @staticmethod
    def gather_patch(patch_dir):
        res = {}
        empty = 0
        for patch_file in os.listdir(patch_dir):
            with open(os.path.join(patch_dir, patch_file), encoding = "utf-8") as f:
                patch = f.read().replace("""PS>
PS>prompt""", "").replace("git --no-pager diff HEAD --diff-filter=M --text", "")
                start = patch.find("diff --git")
                patch = patch[start:]
                res[patch_file.strip(".diff")] = {"model_patch": patch}
                if not patch.strip():
                    empty += 1
        print(f"Collected {len(res)} patches with {empty} empty.")
        return res
    
    def rollout(self, instance: dict[str, Any]):
        '''
        Input:
        SWE-bench format instance dict

        Returns:
        patch diff
        '''

        container: Runtime = Runtime.from_launch_image(instance["docker_image"], 
                                                    instance["instance_id"], 
                                                    partial(self.logger, instance["instance_id"]), 
                                                    self.platform)
        self.install_py(container) # for tool call utils
        self.init_git(container) # to isolate agent's edits
        self.set_mnt_permissions(container)

        prompt = self.prompt_template.replace("_PROBLEM_STATEMENT_", instance["problem_statement"])
        messages =  [
            {"role": "system", "content": "You are an expert software engineer."},
            {"role": "user", "content": prompt},
        ]
        self.logger(instance["instance_id"], json.dumps(messages, indent=True))

        try:
            for step in range(self.max_steps):
                self.logger(instance["instance_id"], f"Step {step}...")
                response: Message = self.llm.query(messages)
                response_dict = response.model_dump()
                self.logger(instance["instance_id"], json.dumps(response_dict, indent = True))
                tool_calls: Optional[list[ChatCompletionMessageToolCall]] = response.tool_calls
                user_messages, submit = self.tools.tool_call(container, tool_calls)
                self.logger(instance["instance_id"], json.dumps(user_messages, indent = True))
                if submit:
                    self.exit_status[instance["instance_id"]] = "submitted"
                    break
                # form next round of messages
                messages.append(response_dict)
                messages.extend(user_messages)
            else:
                self.exit_status[instance["instance_id"]] = "exit_cost"

        except Exception as e:
            err = f"{e}\n{traceback.format_exc()}\nPatch not saved.\n"
            self.logger(instance["instance_id"], err)
            self.exit_status[instance["instance_id"]] = "error"
            print(err)
        finally:
            self.save_patch(container, instance["instance_id"])
            container.cleanup()

        return 
    
    def run_dataset(self, instances: list[dict[str, Any]]):
        if os.path.exists(f"output/{self.run_id}/exit_status.json"):
            with open(f"output/{self.run_id}/exit_status.json") as f:
                s = f.read()
                if s.strip():
                    old_status = json.loads(s)
                    self.exit_status.update(old_status)
        for instance in instances:
            print(f"Running on instance {instance['instance_id']}...")
            patch_file = f"output/{self.run_id}/patch/{instance['instance_id']}.diff"
            if os.path.exists(patch_file) and self.exit_status[instance['instance_id']] != "error":
                print(f"Skipping {instance['instance_id']} ...")
                continue
            try:
                self.rollout(instance)
            except Exception as e:
                err = f"{e}\n{traceback.format_exc()}\nPatch not saved.\n"
                self.logger(instance["instance_id"], err)
                print(err)
                self.exit_status[instance["instance_id"]] = "error"
            with open(f"output/{self.run_id}/exit_status.json", "w") as f:
                json.dump(self.exit_status, f, indent = True)
        with open(f"output/{self.run_id}/preds.json", encoding = "utf-8") as f:
            json.dump(self.gather_patch(f"output/{self.run_id}/patch"), f, indent = True)



