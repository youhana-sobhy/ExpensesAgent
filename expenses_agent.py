from dotenv import load_dotenv
from anthropic import Anthropic
import json, datetime, os

load_dotenv()  # بيقرا ANTHROPIC_API_KEY من ملف .env

client = Anthropic()
model = "claude-sonnet-5-5"

FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "expenses.json")
DEBUG = True  # خليها False لما تفهم اللي بيحصل


# ---------------------------------------------------------------
# 1) الـ tools الحقيقية (إنت اللي بتنفذها، مش Claude)
# ---------------------------------------------------------------

def load():
    if not os.path.exists(FILE):
        return []
    with open(FILE, encoding="utf-8") as f:
        return json.load(f)


def save(data):
    with open(FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def add_expense(amount, category, note="", date=None):
    if amount <= 0:
        raise ValueError("amount must be a positive number")
    data = load()
    expense = {
        "id": max((e["id"] for e in data), default=0) + 1,
        "amount": amount,
        "category": category.lower(),
        "note": note,
        "date": date or datetime.date.today().isoformat(),
    }
    data.append(expense)
    save(data)
    return expense


def _filter(category=None, month=None, date=None):
    items = load()
    if category:
        items = [e for e in items if e["category"] == category.lower()]
    if month:  # صيغة "2026-11"
        items = [e for e in items if e["date"].startswith(month)]
    if date:  # صيغة "2026-11-05"
        items = [e for e in items if e["date"] == date]
    return items


def get_expenses(category=None, month=None, date=None):
    return _filter(category, month, date)


def get_total(category=None, month=None, date=None):
    items = _filter(category, month, date)
    return {"total": sum(e["amount"] for e in items), "count": len(items)}


def get_current_date():
    return datetime.date.today().isoformat()


TOOL_FUNCS = {
    "add_expense": add_expense,
    "get_expenses": get_expenses,
    "get_total": get_total,
    "get_current_date": get_current_date,
}


def run_tool(name, tool_input):
    if name not in TOOL_FUNCS:
        raise ValueError(f"Unknown tool: {name}")
    return TOOL_FUNCS[name](**tool_input)


# ---------------------------------------------------------------
# 2) الـ schemas (التمرين 2: جرّب تخلي الـ descriptions وحشة وشوف الفرق)
# ---------------------------------------------------------------

tools = [
    {
        "name": "get_current_date",
        "description": (
            "Returns today's date in YYYY-MM-DD format. Call this first whenever "
            "the user uses relative time like 'today', 'yesterday', 'this month' "
            "or 'last month', so you can compute the exact date or month."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "add_expense",
        "description": (
            "Records a new expense in the user's expense log. Use when the user "
            "says they spent money on something. Returns the saved record with "
            "its id. Does not read or sum existing expenses."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "amount": {
                    "type": "number",
                    "description": "Amount spent in EGP. Must be positive.",
                },
                "category": {
                    "type": "string",
                    "description": "Short lowercase English category, e.g. food, transport, bills, shopping.",
                },
                "note": {
                    "type": "string",
                    "description": "Optional free-text detail about the expense.",
                },
                "date": {
                    "type": "string",
                    "description": "Optional date as YYYY-MM-DD. Omit for today. Use for past dates like 'yesterday'.",
                },
            },
            "required": ["amount", "category"],
        },
    },
    {
        "name": "get_expenses",
        "description": (
            "Lists individual expense records, optionally filtered. Use when the "
            "user wants to SEE the expenses (what, when, notes). For just a sum, "
            "use get_total instead. All filters are optional and combine with AND."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "category": {"type": "string", "description": "Category to filter by, e.g. food."},
                "month": {"type": "string", "description": "Month as YYYY-MM, e.g. 2026-11."},
                "date": {"type": "string", "description": "Exact day as YYYY-MM-DD."},
            },
        },
    },
    {
        "name": "get_total",
        "description": (
            "Returns the total amount spent and the number of expenses, optionally "
            "filtered by category, month or exact date. Use for questions like "
            "'how much did I spend on...'. Does not return individual records."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "category": {"type": "string", "description": "Category to filter by, e.g. transport."},
                "month": {"type": "string", "description": "Month as YYYY-MM, e.g. 2026-11."},
                "date": {"type": "string", "description": "Exact day as YYYY-MM-DD."},
            },
        },
    },
]


# ---------------------------------------------------------------
# 3) الـ messages helpers والـ loop
# ---------------------------------------------------------------

def add_user_message(messages, content):
    # content ممكن يكون string أو list of blocks (للـ tool_result)
    messages.append({"role": "user", "content": content})


def add_assistant_message(messages, content):
    # لازم الـ list كاملة بما فيها tool_use blocks
    messages.append({"role": "assistant", "content": content})


def chat(messages, system=None, tool_choice=None):
    params = {
        "model": model,
        "max_tokens": 1000,
        "messages": messages,
        "tools": tools,
    }
    if system:
        params["system"] = system
    if tool_choice:  # التمرين 6: {"type":"auto"} / {"type":"any"} / {"type":"tool","name":"get_total"}
        params["tool_choice"] = tool_choice
    return client.messages.create(**params)


def dump(messages):
    def default(o):
        return o.model_dump() if hasattr(o, "model_dump") else str(o)
    print(json.dumps(messages, ensure_ascii=False, indent=2, default=default))
    print("-" * 60)


def run_conversation(messages, tool_choice=None):
    while True:
        response = chat(messages, tool_choice=tool_choice)
        add_assistant_message(messages, response.content)
        if DEBUG:
            print(f"stop_reason = {response.stop_reason}")
            dump(messages)

        if response.stop_reason != "tool_use":
            return "".join(b.text for b in response.content if b.type == "text")

        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                try:
                    result = run_tool(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result, ensure_ascii=False),
                    })
                except Exception as e:
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": f"Error: {e}",
                        "is_error": True,
                    })
        # كل الـ results في رسالة user واحدة
        add_user_message(messages, tool_results)

        # tool_choice "any" أو tool محددة هتخلي Claude يطلب tool في كل لفة،
        # فبنرجعها auto بعد أول مرة عشان اللوب يخلص
        tool_choice = None


if __name__ == "__main__":
    messages = []
    print("Expense assistant. اكتب 'exit' للخروج.")
    while True:
        text = input("\nYou: ").strip()
        if text.lower() in ("exit", "quit", ""):
            break
        add_user_message(messages, text)
        print("\nClaude:", run_conversation(messages))