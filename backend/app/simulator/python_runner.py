import ast
import sys
from app.simulator.mission_engine import MissionState, execute_command, execute_enemy_wait
from app.schemas.game import Command
from app.simulator.mechanics import clear_shot

class TimeoutException(Exception):
    pass


ALLOWED_CALLS = {"move", "rotate", "fire", "scan", "range"}
ALLOWED_NODES = (
    ast.Module, ast.Expr, ast.Call, ast.Name, ast.Load, ast.Store, ast.Constant,
    ast.If, ast.For, ast.While, ast.Compare, ast.Eq, ast.NotEq, ast.Lt, ast.LtE,
    ast.Gt, ast.GtE, ast.BoolOp, ast.And, ast.Or, ast.UnaryOp, ast.Not,
    ast.Assign, ast.Pass,
)


def validate_user_code(code: str) -> ast.Module:
    """Accept only the small Python subset used by tank strategies."""
    tree = ast.parse(code, mode="exec")
    for node in ast.walk(tree):
        if not isinstance(node, ALLOWED_NODES):
            raise ValueError(f"Unsupported syntax: {type(node).__name__}")
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name) or node.func.id not in ALLOWED_CALLS:
                raise ValueError("Only move, rotate, fire, scan and range calls are allowed")
            if node.keywords:
                raise ValueError("Keyword arguments are not allowed")
        if isinstance(node, ast.Name) and node.id.startswith("__"):
            raise ValueError("Private names are not allowed")
    return tree

def run_user_code(code: str, state: MissionState) -> dict:
    """
    Executes user python code in a sandbox.
    Captures tank actions and returns a replay.
    """
    ticks = []
    
    def _do_command(name: str, turn: str | None = None) -> bool:
        # If player is dead, skip execution but return False to indicate failure
        if state.tank.hp <= 0:
            return False
            
        result = execute_command(state, Command(name=name, turn=turn))
        ticks.append(result.model_dump())
        return result.ok

    def py_move():
        return _do_command("move")
        
    def py_rotate(turn="RIGHT"):
        normalized = str(turn).upper()
        if normalized not in ("LEFT", "RIGHT"):
            raise ValueError("rotate() accepts only 'LEFT' or 'RIGHT'")
        return _do_command("rotate", normalized)
        
    def py_fire():
        return _do_command("fire")
        
    def py_scan():
        visible = any(
            enemy.alive
            and clear_shot(
                state.tank.x, state.tank.y, enemy.x, enemy.y, state.walls
            )
            for enemy in state.enemies
        )
        _do_command("scan")
        return visible
        
    safe_globals = {
        "__builtins__": {},
        "move": py_move,
        "rotate": py_rotate,
        "fire": py_fire,
        "scan": py_scan,
        "range": range,
        "print": lambda *args: None, # Prevent print spam
    }
    
    # Execution limiter
    step_count = 0
    def trace_calls(frame, event, arg):
        nonlocal step_count
        step_count += 1
        if step_count > 5000:
            raise TimeoutException("Execution limit exceeded (infinite loop?)")
        return trace_calls

    error = None
    sys.settrace(trace_calls)
    try:
        tree = validate_user_code(code)
        exec(compile(tree, "player_strategy.py", "exec"), safe_globals)
    except TimeoutException as e:
        error = str(e)
    except Exception as e:
        error = f"Error in python script: {str(e)}"
    finally:
        sys.settrace(None)

    # The player's program runs exactly once. After it ends, only enemies keep
    # taking turns so the battle itself still lasts up to 30 seconds.
    if error is None:
        while len(ticks) < 72 and state.tank.hp > 0:
            ticks.append(execute_enemy_wait(state).model_dump())
        
    return {
        "ticks": ticks,
        "error": error
    }
