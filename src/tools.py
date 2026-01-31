import json
from typing import Any, Optional

from litellm import ChatCompletionMessageToolCall, Message

from src.runtime import Runtime

from src.tool_set.base import Tool
from src.tool_set.shell import Shell
from src.tool_set.read import Read
from src.tool_set.create import Create
from src.tool_set.string_replace import Replace
from src.tool_set.submit import Submit


class Tools:
    tool_dict: dict[str, Tool] = {
        "shell": Shell,
        "read": Read,
        "create": Create,
        "string_replace": Replace,
        "submit": Submit,
    }

    def __init__(self, available_tools: list[str]):
        self.available_tools: list[str] = available_tools
        if "submit" not in self.available_tools:
            self.available_tools.append("submit")
        self.tools: list[dict[str, Any]] = [self.tool_dict[i].tool for i in self.available_tools]

    def tool_call(self, 
                  container: Runtime, 
                  tool_calls: Optional[list[ChatCompletionMessageToolCall]]
                ) -> tuple[list[Message], bool]:
        '''
        Returns: 
        (Tool result messages , Submit or not)
        '''
        
        if tool_calls is None or len(tool_calls) == 0:
            return [{
                        "role": "user",
                        "content": "Each of your response should have exactly one tool call. Plase generate one tool call.",
                }], False
        if len(tool_calls) > 1:
            messages = []
            for tool_call in tool_calls:
                function_name = tool_call.function.name
                messages.append(
                    {
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": "Each of your response should have exactly one tool call. Plase generate only one tool call next time.",
                    }
                )
            return messages, False
        
        tool_call = tool_calls[0]
        function_name = tool_call.function.name
        
        if function_name.strip().lower() == "submit":
            return [], True
        
        if function_name not in self.available_tools:
            return [
                {
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": function_name,
                    "content": f"tool call name not found, available tools: {self.available_tools}",
                }
            ], False
        
        try:
            function_args = json.loads(tool_call.function.arguments)
        except:
            return [
                {
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": function_name,
                    "content": f"tool call arguments have json decode error: {tool_call.function.arguments}",
                }
            ], False
        final_res = [
            {
                "tool_call_id": tool_call.id,
                "role": "tool",
                "name": function_name,
                "content": self.tool_dict[function_name].tool_call(container, function_args),
            }
        ]
        return final_res, False