
import yaml, json
from typing import Any
from datasets import load_dataset
from argparse import ArgumentParser
from src.agent import Agent


def main(config: dict[str, Any]) -> None:
    run_id = f"{config['dataset']}_{config['model']}".replace("/", "_").replace("\\", "_")
    if config["dataset"].endswith(".json") or config["dataset"].endswith(".jsonl"):
        with open(config["dataset"], "r", encoding="utf-8") as f:
            if config["dataset"].endswith(".json"):
                instances = json.load(f)
            else:
                instances = [json.loads(line) for line in f]
    else:
        instances: list[dict[str, Any]] = load_dataset(config["dataset"], split = config.get("split", None))
    
    agent = Agent(config["model"], 
                  config["api_key"], 
                  config["base_url"],
                  config["tools"], 
                  config["prompt"], 
                  config["max_steps"],
                  config.get("workers", 1),
                  config.get("instance_timeout", 480),
                  config["platform"],
                  run_id)
    if not config["gather_patch"]:
        agent.run_dataset(instances)
    else:
        print("Dry run to collect exeisting patch submissions...")
        agent.gather_then_save_patch()

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--config_path", type=str, default="config/default.yaml")
    parser.add_argument("--api_key", type=str, default = "None")
    parser.add_argument("--collect_patch", action="store_true")
    args = parser.parse_args()
    with open(args.config_path) as f:
        config = yaml.safe_load(f)
    config["api_key"] = args.api_key
    config["gather_patch"] = args.collect_patch
    main(config)