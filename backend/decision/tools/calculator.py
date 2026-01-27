"""Safe calculator tool for expert agents.

Provides AST-based arithmetic evaluation so experts can compute costs,
projections, and other numerical analyses without resorting to ``eval``.
"""

from __future__ import annotations

import ast
import math
import operator
from typing import Union

from langchain_core.tools import tool

# ---------------------------------------------------------------------------
# Operator / function whitelists
# ---------------------------------------------------------------------------

_SAFE_BINOPS: dict[type, object] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}

_SAFE_UNARYOPS: dict[type, object] = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}

_SAFE_FUNCTIONS: dict[str, object] = {
    "abs": abs,
    "round": round,
    "min": min,
    "max": max,
    "sum": sum,
    "int": int,
    "float": float,
    "sqrt": math.sqrt,
    "log": math.log,
    "log10": math.log10,
    "ceil": math.ceil,
    "floor": math.floor,
}

# ---------------------------------------------------------------------------
# Safe evaluator
# ---------------------------------------------------------------------------


def _safe_eval(node: ast.AST) -> Union[int, float]:
    """Recursively evaluate an AST node using only whitelisted operations."""

    # Numeric literals
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value

    # Binary operations (a + b, etc.)
    if isinstance(node, ast.BinOp):
        op_func = _SAFE_BINOPS.get(type(node.op))
        if op_func is None:
            raise ValueError(f"Unsupported binary operator: {type(node.op).__name__}")
        left = _safe_eval(node.left)
        right = _safe_eval(node.right)
        return op_func(left, right)  # type: ignore[operator]

    # Unary operations (+x, -x)
    if isinstance(node, ast.UnaryOp):
        op_func = _SAFE_UNARYOPS.get(type(node.op))
        if op_func is None:
            raise ValueError(f"Unsupported unary operator: {type(node.op).__name__}")
        return op_func(_safe_eval(node.operand))  # type: ignore[operator]

    # Function calls (sqrt(4), min(1, 2, 3), etc.)
    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name):
            raise ValueError("Only simple function calls are allowed (no methods or attribute access).")
        func_name = node.func.id
        func = _SAFE_FUNCTIONS.get(func_name)
        if func is None:
            raise ValueError(f"Function not allowed: {func_name}")
        args = [_safe_eval(arg) for arg in node.args]
        return func(*args)  # type: ignore[operator]

    # List literals (for min/max/sum)
    if isinstance(node, ast.List):
        return [_safe_eval(el) for el in node.elts]  # type: ignore[return-value]

    # Tuple literals (for min/max)
    if isinstance(node, ast.Tuple):
        return tuple(_safe_eval(el) for el in node.elts)  # type: ignore[return-value]

    raise ValueError(
        f"Unsupported expression type: {type(node).__name__}. "
        "Only arithmetic operations and whitelisted functions are allowed."
    )


# ---------------------------------------------------------------------------
# Tool factory
# ---------------------------------------------------------------------------


def create_calculator_tool():
    """Return a LangChain tool that safely evaluates arithmetic expressions."""

    @tool("calculator")
    def calculator(expression: str) -> str:
        """Evaluate a mathematical expression safely.

        Supports basic arithmetic (+, -, *, /, //, %, **) and functions:
        abs, round, min, max, sum, int, float, sqrt, log, log10, ceil, floor.

        Args:
            expression: A mathematical expression, e.g. ``500000 * 1.05 ** 5``.
        """
        try:
            tree = ast.parse(expression.strip(), mode="eval")
        except SyntaxError as exc:
            return f"Error: invalid expression -- {exc}"

        try:
            result = _safe_eval(tree.body)
        except (ValueError, TypeError, ZeroDivisionError, OverflowError) as exc:
            return f"Error: {exc}"

        return f"{expression.strip()} = {result}"

    return calculator
