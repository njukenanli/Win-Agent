from typing import Any
import time
import litellm
from litellm.types.utils import ModelResponse, Message

class LLM:
    def __init__(self, model: str, api_key: str, base_url: str|None, tools: list[dict[str, Any]]):
        self.model = model
        self.api_key = api_key
        self.tools = tools
        self.base_url = base_url
    def query(self, messages: list[dict[str, Any]]) -> Message:
        """
        Query an LLM using litellm.
        
        Args:
            model: The model identifier (e.g., "gpt-4", "claude-3-opus")
            api_key: The API key for the model provider
            messages: List of message dicts with 'role' and 'content'
            tools: List of tool definitions for function calling
        
        Returns:
            The response message from the LLM, or None if all retries failed
        """
        max_retries = 5
        retry_interval = 60
        
        for attempt in range(max_retries):
            try:
                response: ModelResponse = litellm.completion(
                    model=self.model,
                    api_key=self.api_key,
                    base_url=self.base_url,
                    messages=messages,
                    tools=self.tools,
                    tool_choice="auto",
                )
                return response.choices[0].message
            except Exception as e:
                print(f"Litellm query attempt {attempt + 1}/{max_retries} failed: {e}")
                if attempt < max_retries - 1:
                    print(f"Retrying in {retry_interval} seconds...")
                    time.sleep(retry_interval)
                else:
                    raise e