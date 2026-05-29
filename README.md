
```bash
pip install -r requirements.txt
```

To run on Windows container, download Docker Desktop, start it, and switch to Windows container mode.

### Rollout

For windows:
```powershell
$env:PYTHONUTF8="1" 
$env:PYTHONIOENCODING="utf-8"
python main.py --config_path config/gpt55.yaml
```

```powershell
$env:PYTHONUTF8="1"
$env:PYTHONIOENCODING="utf-8"
python main.py --config_path config/ds4pro.yaml
```

Patch submissions will be saved to output/{run_id}/preds.json

If the rollout is interrupted, to collect existing patches instead of proceeding to rollout, please use the following flag for dry run.

```bash
python main.py --config_path config/gpt55.yaml --collect_patch 
```

