from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

from anthropic import Anthropic
from anthropic.types import ToolParam

client = Anthropic()
model = "claude-sonnet-4-5"

get_current_datetime_schema = ToolParam({
    "name": "get_current_datetime",
    "description": "Returns the current date and time as a string, formatted according to a Python strftime format string. Use this whenever you need to know the current date, time, or day, since the model has no clock of its own. Takes no required input; if no format is given, returns the time in 'YYYY-MM-DD HH:MM:SS' form.",
    "input_schema": {
        "type": "object",
        "properties": {
            "date_format": {
                "type": "string",
                "description": "A Python strftime format string, e.g. '%Y-%m-%d', '%H:%M', or '%A, %B %d, %Y'. Must be a non-empty string.",
                "default": "%Y-%m-%d %H:%M:%S",
                "minLength": 1,
            }
        },
        "required": [],
        "additionalProperties": False,
    },
})


def get_current_datetime(date_format="%Y-%m-%d %H:%M:%S"):
    if not date_format:
        raise ValueError("date_format cannot be empty")
    return datetime.now().strftime(date_format)


def add_user_message(messages, content):
    # content can be a string OR a list of blocks (needed for tool_result)
    messages.append({"role": "user", "content": content})


def add_assistant_message(messages, content):
    # content must be the full list of blocks, including tool_use blocks
    messages.append({"role": "assistant", "content": content})


def chat(messages, system=None, temperature=1.0):
    params = {
        "model": model,
        "max_tokens": 1000,
        "messages": messages,
        # "temperature": temperature,
        "tools": [get_current_datetime_schema],
    }
    if system:
        params["system"] = system
    return client.messages.create(**params)  # return the whole message


def run_tool(name, tool_input):
    if name == "get_current_datetime":
        return get_current_datetime(**tool_input)
    raise ValueError(f"Unknown tool: {name}")


def run_conversation(messages):
    while True:
        response = chat(messages)
        print(messages)
        print(" ")
        add_assistant_message(messages, response.content)

        if response.stop_reason != "tool_use":
            # Final answer: collect the text blocks
            return "".join(b.text for b in response.content if b.type == "text")

        # Run every tool Claude asked for and send the results back
        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                try:
                    result = run_tool(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": str(result),
                    })
                except Exception as e:
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": f"Error: {e}",
                        "is_error": True,
                    })
        add_user_message(messages, tool_results)


messages = []
add_user_message(messages, "what is the exact time")
print(run_conversation(messages))