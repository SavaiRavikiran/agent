"""Cheap correctness check for arithmetic questions.

Not a substitute for a real eval suite - it only checks whether the question
contains a math expression and, if so, whether the agent's final answer
contains that expression's correct numeric value.
"""
import re
from typing import Tuple

_MATH_PATTERN = re.compile(r"[\d(][\d\s+\-*/().]*[\d)]")
_NUMBER_PATTERN = re.compile(r"-?\d+(\.\d+)?")


def evaluate_answer(question: str, final_answer: str) -> Tuple[float, str]:
    math = _MATH_PATTERN.search(question)
    if not math:
        if final_answer:
            return 1.0, "no arithmetic to check; answer produced"
        return 0.0, "no answer produced"

    try:
        expected = eval(math.group())  # safe: input restricted to digits/operators above
    except Exception as e:
        return 0.0, f"expression itself is invalid ({e})"

    found = _NUMBER_PATTERN.search(final_answer)
    if not found:
        return 0.0, f"no numeric answer found, expected {expected}"

    correct = float(found.group()) == float(expected)
    return (1.0 if correct else 0.0), f"expected {expected}, got {found.group()}"
