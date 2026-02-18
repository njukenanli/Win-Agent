
from functools import partial
import json
import os
from datetime import datetime
import time
import _thread
import threading
import multiprocessing as mp
from multiprocessing.managers import AcquirerProxy
from typing import Any, Literal, Optional

from litellm import ChatCompletionMessageToolCall
from src.runtime import Runtime
from src.llm import LLM
from src.tools import Tools
from litellm.types.utils import ModelResponse, Message
import traceback

from src.utils import Utils

ExitStatus = Literal["submitted", "exit_cost", "exit_timeout", "error"]

class Agent:
    def __init__(self, 
                 model: str, 
                 api_key: str, 
                 base_url: str|None,
                 tools: list[str], 
                 prompt: str, 
                 max_steps: int, 
                 workers: int,
                 instance_timeout: int,
                 platform: Literal["linux", "windows"],
                 run_id: str,
                 write_lock: Optional[Any] = None):
        self.tools = Tools(tools)
        self.llm = LLM(model, api_key, base_url, self.tools.tools)
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self.tool_names = tools
        self.max_steps = max_steps
        self.instance_timeout = instance_timeout # minute
        self.workers = workers
        self.prompt_template = prompt
        self.run_id = run_id
        self.platform = platform
        self.write_lock = write_lock or threading.Lock() # main agent: create lock; sub-process agent: receive lock
        self.exit_status: dict[str, ExitStatus] = {}

    def _set_exit_status(self, instance_id: str, status: ExitStatus) -> None:
        with self.write_lock:
            self.exit_status[instance_id] = status

    def _write_exit_status_file(self) -> None:
        with self.write_lock:
            os.makedirs(f"output/{self.run_id}", exist_ok=True)
            with open(f"output/{self.run_id}/exit_status.json", "w", encoding="utf-8") as f:
                json.dump(self.exit_status, f, indent = True)

    def logger(self, instance_id: str, log: str):
        with self.write_lock:
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
        Utils.reset_cwd(container)
        with self.write_lock:
            os.makedirs(f"output/{self.run_id}/patch", exist_ok=True)

        temp_file = f"mnt/{self.run_id}_{instance_id}.diff"
        container.send_command(f"git --no-pager diff HEAD --diff-filter=M --text > {temp_file}")
        patch = (Utils.safe_read(temp_file)
                .replace("""PS>
PS>prompt""", "").replace("git --no-pager diff HEAD --diff-filter=M --text", ""))
        start = patch.find("diff --git")
        patch = patch[start:]
        patch_file = f"output/{self.run_id}/patch/{instance_id}.diff"
        with self.write_lock:
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

    def gather_then_save_patch(self):
        tgt_path = f"output/{self.run_id}/preds.json"
        with self.write_lock:
            with open(tgt_path, "w", encoding = "utf-8") as f:
                json.dump(self.gather_patch(f"output/{self.run_id}/patch"), f, indent = True)
        print(f"Patch submissions saved to {os.path.abspath(tgt_path)}")

    def _copy_agent_status(self, instance: dict[str, Any], write_lock: AcquirerProxy) -> dict[str, Any]:
        return {
            "model": self.model,
            "api_key": self.api_key,
            "base_url": self.base_url,
            "tools": self.tool_names,
            "prompt": self.prompt_template,
            "max_steps": self.max_steps,
            "workers": self.workers,
            "instance_timeout": self.instance_timeout,
            "platform": self.platform,
            "run_id": self.run_id,
            "instance": instance,
            "write_lock": write_lock,
        }

    @staticmethod
    def _rollout_worker(payload: dict[str, Any]) -> tuple[str, ExitStatus]:
        instance: dict[str, Any] = payload["instance"]
        agent = Agent(
            model=payload["model"],
            api_key=payload["api_key"],
            base_url=payload["base_url"],
            tools=payload["tools"],
            prompt=payload["prompt"],
            max_steps=payload["max_steps"],
            workers=payload["workers"],
            instance_timeout=payload["instance_timeout"],
            platform=payload["platform"],
            run_id=payload["run_id"],
            write_lock=payload["write_lock"],
        )
        try:
            agent.rollout(instance)
        except Exception as e:
            err = f"{e}\n{traceback.format_exc()}\nPatch not saved.\n"
            agent.logger(instance["instance_id"], err)
            print(err)
            agent._set_exit_status(instance["instance_id"], "error")
        status: ExitStatus = agent.exit_status.get(instance["instance_id"], "error")
        return instance["instance_id"], status

    def _start_timeout_watchdog(self) -> tuple[threading.Event, threading.Event, threading.Thread]:
        timeout_event = threading.Event()
        cancel_timeout_event = threading.Event()

        def timeout_watchdog() -> None:
            if cancel_timeout_event.wait(timeout=self.instance_timeout * 60):
                return
            timeout_event.set()
            _thread.interrupt_main()

        timer_thread = threading.Thread(
            target=timeout_watchdog,
            daemon=True,
            name="instance-timeout-watchdog",
        )
        timer_thread.start()
        return timeout_event, cancel_timeout_event, timer_thread
    
    def rollout(self, instance: dict[str, Any]) -> None:
        '''
        Input:
        SWE-bench format instance dict

        Returns:
        patch diff
        '''

        print(f"Running on instance {instance['instance_id']}...")
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

        timeout_event, cancel_timeout_event, timer_thread = self._start_timeout_watchdog()

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
                    self._set_exit_status(instance["instance_id"], "submitted")
                    break
                # form next round of messages
                messages.append(response_dict)
                messages.extend(user_messages)
            else:
                self._set_exit_status(instance["instance_id"], "exit_cost")

        except KeyboardInterrupt:
            if timeout_event.is_set():
                raise TimeoutError
            raise
        except TimeoutError:
            err = f"Exceed instance timeout of {self.instance_timeout} minutes"
            self.logger(instance["instance_id"], err)
            self._set_exit_status(instance["instance_id"], "exit_timeout")
            print(err)
        except Exception as e:
            err = f"{e}\n{traceback.format_exc()}\nPatch might not be saved.\n"
            self.logger(instance["instance_id"], err)
            self._set_exit_status(instance["instance_id"], "error")
            print(err)
        finally:
            cancel_timeout_event.set()
            timer_thread.join()
            self.save_patch(container, instance["instance_id"])
            container.cleanup()

        return 
    
    def run_dataset(self, instances: list[dict[str, Any]]):
        if os.path.exists(f"output/{self.run_id}/exit_status.json"):
            with self.write_lock:
                with open(f"output/{self.run_id}/exit_status.json", encoding="utf-8") as f:
                    s = f.read()
                    if s.strip():
                        old_status = json.loads(s)
                        self.exit_status.update(old_status)

        pending_instances: list[dict[str, Any]] = []
        for instance in instances:
            instance_id = instance["instance_id"]
            patch_file = f"output/{self.run_id}/patch/{instance_id}.diff"
            if os.path.exists(patch_file) and self.exit_status.get(instance_id, "error") != "error":
                print(f"Skipping {instance_id} ...")
                continue
            pending_instances.append(instance)

        if self.workers <= 1:
            for instance in pending_instances:
                try:
                    self.rollout(instance)
                except Exception as e:
                    err = f"{e}\n{traceback.format_exc()}\nPatch not saved.\n"
                    self.logger(instance["instance_id"], err)
                    print(err)
                    self._set_exit_status(instance["instance_id"], "error")
                self._write_exit_status_file()
        else:
            ctx = mp.get_context("spawn")
            original_lock = self.write_lock
            with ctx.Manager() as manager:
                shared_lock = manager.Lock()
                self.write_lock = shared_lock
                payloads = [self._copy_agent_status(instance, shared_lock) for instance in pending_instances]
                with ctx.Pool(processes=self.workers) as pool:
                    for instance_id, status in pool.imap_unordered(Agent._rollout_worker, payloads):
                        print(f"Completed {instance_id} with status {status}")
                        self._set_exit_status(instance_id, status)
                        self._write_exit_status_file()
            self.write_lock = original_lock

        self.gather_then_save_patch()



