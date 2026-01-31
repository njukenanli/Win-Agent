
import yaml
from typing import Any
from datasets import load_dataset
from argparse import ArgumentParser
from src.agent import Agent


def main(config: dict[str, Any]) -> None:
    run_id = f"{config['dataset']}_{config['model']}".replace("/", "_").replace("\\", "_")
    instances: list[dict[str, Any]] = load_dataset(config["dataset"], split = "test")
    agent = Agent(config["model"], 
                  config["api_key"], 
                  config["base_url"],
                  config["tools"], 
                  config["prompt"], 
                  config["max_steps"],
                  config["platform"],
                  run_id)
    agent.run_dataset(instances)

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--config_path", type=str, default="config/default.yaml")
    parser.add_argument("--api_key", type=str, default = "None")
    args = parser.parse_args()
    with open(args.config_path) as f:
        config = yaml.safe_load(f)
    config["api_key"] = args.api_key
    main(config)