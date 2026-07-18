from __future__ import annotations

import ast
from collections.abc import Callable, Iterator

from app.simulator.python_runner import validate_user_code


TANK_ACTIONS = {"move", "fire", "scan"}


def iter_strategy_actions(code: str, scan_visible: Callable[[], bool]) -> Iterator[str]:
    """Parse the shared Challenge/PvP Python subset into live tank actions."""
    tree = validate_user_code(code)

    def scan_condition(test: ast.expr) -> bool:
        return (
            isinstance(test, ast.Call)
            and isinstance(test.func, ast.Name)
            and test.func.id == "scan"
            and not test.args
            and not test.keywords
        )

    def call_action(call: ast.Call) -> str:
        if not isinstance(call.func, ast.Name):
            raise ValueError("Only tank command calls are supported")
        name = call.func.id
        if name in TANK_ACTIONS:
            if call.args:
                raise ValueError(f"{name}() does not accept arguments")
            return name
        if name == "rotate":
            if len(call.args) > 1:
                raise ValueError("rotate() accepts at most one argument")
            if not call.args:
                return "rotate_right"
            argument = call.args[0]
            if not isinstance(argument, ast.Constant) or str(argument.value).upper() not in {
                "LEFT",
                "RIGHT",
            }:
                raise ValueError("rotate() accepts only 'LEFT' or 'RIGHT'")
            return f"rotate_{str(argument.value).lower()}"
        raise ValueError(f"Unsupported strategy call: {name}()")

    def range_count(statement: ast.For) -> int:
        iterator = statement.iter
        if (
            not isinstance(iterator, ast.Call)
            or not isinstance(iterator.func, ast.Name)
            or iterator.func.id != "range"
            or not 1 <= len(iterator.args) <= 3
            or any(
                not isinstance(argument, ast.Constant)
                or not isinstance(argument.value, int)
                for argument in iterator.args
            )
        ):
            raise ValueError("for loops require range() with 1 to 3 integer constants")
        values = [argument.value for argument in iterator.args]
        try:
            return min(len(range(*values)), 40)
        except ValueError as error:
            raise ValueError(f"Invalid range(): {error}") from error

    def validate_block(statements: list[ast.stmt]) -> None:
        for statement in statements:
            if isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Call):
                call_action(statement.value)
            elif isinstance(statement, ast.For):
                range_count(statement)
                validate_block(statement.body)
                validate_block(statement.orelse)
            elif isinstance(statement, (ast.If, ast.While)):
                if not scan_condition(statement.test):
                    raise ValueError("if and while conditions must use scan()")
                validate_block(statement.body)
                validate_block(statement.orelse)
            elif isinstance(statement, ast.Pass):
                continue
            else:
                raise ValueError(f"Unsupported strategy statement: {type(statement).__name__}")

    validate_block(tree.body)

    def execute_block(statements: list[ast.stmt]) -> Iterator[str]:
        for statement in statements:
            if isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Call):
                yield call_action(statement.value)
            elif isinstance(statement, ast.For):
                for _ in range(range_count(statement)):
                    yield from execute_block(statement.body)
            elif isinstance(statement, ast.If):
                yield "scan"
                branch = statement.body if scan_visible() else statement.orelse
                yield from execute_block(branch)
            elif isinstance(statement, ast.While):
                for _ in range(40):
                    yield "scan"
                    if not scan_visible():
                        break
                    yield from execute_block(statement.body)

    return execute_block(tree.body)
