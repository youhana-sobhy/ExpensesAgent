# Expenses Agent

My first AI agent — a conversational expense tracker powered by Claude (Anthropic API) and tool use.

You talk to it in plain language (English or Arabic), and it decides which tools to call to record and analyze your spending:

```
You: I spent 120 on lunch today
You: how much did I spend on food this month?
You: show me all transport expenses from last month
```

## How it works

The agent runs a simple **agent loop**:

1. Your message is sent to Claude together with a list of available tools.
2. If Claude decides it needs a tool, it returns a `tool_use` request.
3. The script runs the matching Python function and sends back a `tool_result`.
4. This repeats until Claude has everything it needs and replies with a final answer.

### Tools

| Tool | What it does |
|------|--------------|
| `get_current_date` | Returns today's date so the agent can resolve "today", "yesterday", "this month" |
| `add_expense` | Saves a new expense (amount, category, note, date) |
| `get_expenses` | Lists expenses filtered by category, month, or date |
| `get_total` | Returns the total spent and count for a filter |

Expenses are stored locally in [`data/expenses.json`](data/expenses.json).

## Project structure

```
.
├── expenses_agent.py              # Main agent: tools, schemas, and agent loop
├── data/
│   └── expenses.json              # Local expense storage (sample data included)
├── examples/
│   ├── 01_basic_chat.py           # First step: a simple multi-turn chat with Claude
│   └── 02_tool_use_datetime.py    # Second step: a single tool + the tool-use loop
├── notebooks/
│   └── 01_getting_started.ipynb   # First API call experiments
├── requirements.txt
└── .env.example
```

The `examples/` folder shows how the project grew: from a basic API call, to a single tool, to a full multi-tool agent.

## Getting started

1. Clone the repo and create a virtual environment:

   ```bash
   python -m venv .venv
   .venv\Scripts\activate      # Windows
   # source .venv/bin/activate # macOS / Linux
   pip install -r requirements.txt
   ```

2. Add your API key — copy `.env.example` to `.env` and fill in your key from the [Anthropic Console](https://console.anthropic.com/):

   ```
   ANTHROPIC_API_KEY=your-api-key-here
   ```

   `.env` is listed in `.gitignore`, so your key is never committed.

3. Run the agent:

   ```bash
   python expenses_agent.py
   ```

   Type `exit` to quit. Set `DEBUG = False` in `expenses_agent.py` to hide the raw message dumps.

## What I learned

- Calling the Claude Messages API and managing conversation history
- Writing clear tool schemas and descriptions so the model picks the right tool
- Building the tool-use loop (`tool_use` → run function → `tool_result`)
- Handling tool errors gracefully with `is_error`
- Controlling tool selection with `tool_choice`
