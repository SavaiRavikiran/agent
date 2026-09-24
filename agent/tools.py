"""Tools available to the agent."""
import re
from datetime import datetime, timezone

from langchain_core.tools import tool

_ALLOWED_EXPRESSION = re.compile(r"[\d\s+\-*/().]+")


@tool
def calculator(expression: str) -> str:
    """Evaluate a basic math expression, e.g. '23 * 47 + 10'."""
    if not _ALLOWED_EXPRESSION.fullmatch(expression):
        return "Error: only numbers and + - * / ( ) are allowed"
    try:
        return str(eval(expression))  # safe: input restricted to digits/operators above
    except ZeroDivisionError:
        return "Error: division by zero"
    except Exception as e:  # malformed expression, e.g. "(("
        return f"Error: {e}"


@tool
def current_time() -> str:
    """Return the current UTC date and time."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


TOOLS = [calculator, current_time]
