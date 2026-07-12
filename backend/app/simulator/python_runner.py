import sys
from app.simulator.mission_engine import MissionState, execute_command, execute_enemy_wait
from app.schemas.game import Command

class TimeoutException(Exception):
    pass

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
        # Scan executes as a command (taking a turn), and returns a boolean (enemy visible)
        _do_command("scan")
        # In current logic, scan just returns True if enemy is alive.
        # Let's provide a slightly more useful boolean for python scripters:
        # returns True if enemy is in the current line of sight or alive? 
        # Actually `execute_command` logs the distance if alive. 
        # We will just return True if enemy is alive for backward compatibility with MVP.
        return state.enemy.alive
        
    safe_globals = {
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
        exec(code, safe_globals)
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
