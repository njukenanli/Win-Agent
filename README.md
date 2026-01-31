# Win-Agent: A SWE agent compatible on both Windows and Linux containers

## Setup

```bash
pip install -r requirements.txt
```

To run on Windows container, download Docker Desktop, start it, and switch to Windows container mode.


## Run

Prepare your config file. A template is config/default.yaml

### model configs
openrouter model: 

    model: openrouter/deepseek/deepseek-v3.1-terminus
    base_url: https://openrouter.ai/api/v1

### Rollout

For windows:
```powershell
$env:PYTHONUTF8="1" 
$env:PYTHONIOENCODING="utf-8" 
```

```bash
python main.py --config_path config/default.yaml --api_key ...
```


## Customize tool set

Modify src/tools.py

The shared folder of host and sandbox container where a built repo lies is ./mnt