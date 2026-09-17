import os
from state import AgentState, TaskResult
from db import execute_query

# Universal Import for interrupt
try:
    from langgraph.types import interrupt
except ImportError:
    try:
        from langgraph.constants import interrupt
    except ImportError:
        try:
            from langgraph import interrupt
        except ImportError:
            # Fallback for very old versions of langgraph on Render
            def interrupt(value):
                print("Warning: interrupt() not supported in this langgraph version. Bypassing HITL.")
                return "approve" 

# Universal Import for Command
try:
    from langgraph.constants import Command
except ImportError:
    try:
        from langgraph.types import Command
    except ImportError:
        try:
            from langgraph import Command
        except ImportError:
            Command = None

def executor_node(state: AgentState):
    sql_query = state.get("current_sql_query", "")
    guard_keyword = state.get("guard_keyword", "update")
    force_execute = state.get("force_execute", False)
    task_list = state.get("task_list", [])
    idx = state.get("current_task_index", 0)
    
    if idx >= len(task_list):
        return {}

    task = task_list[idx]

    # HITL logic
    if guard_keyword == "ask_before_running" and not force_execute:
        # We trigger an interrupt. The value passed to interrupt is what the user sees.
        # The value returned by interrupt is what the user provides.
        hitl_payload = {
            "task_id": task["task_id"],
            "sql_query": sql_query,
            "description": task["description"]
        }
        
        # Pause graph and wait for "approve" or "reject"
        hitl_response = interrupt(hitl_payload)
        
        if hitl_response == "reject":
            result = TaskResult(
                task_id=task["task_id"],
                description=task["description"],
                sql_query=sql_query,
                result=None,
                error="rejected by user"
            )
            # Update task status
            new_tasks = list(task_list)
            new_tasks[idx]["status"] = "failed"
            
            return {
                "accumulated_results": state.get("accumulated_results", []) + [result],
                "task_list": new_tasks,
                "current_task_index": idx + 1,
                "hitl_pending": False
            }

    # Direct Execution (safe or forced)
    execution_result = execute_query(sql_query)
    
    if isinstance(execution_result, str) and execution_result.startswith("Error:"):
        result = TaskResult(
            task_id=task["task_id"],
            description=task["description"],
            sql_query=sql_query,
            result=None,
            error=execution_result
        )
        status = "failed"
    else:
        result = TaskResult(
            task_id=task["task_id"],
            description=task["description"],
            sql_query=sql_query,
            result=execution_result,
            error=None
        )
        status = "done"

    # Update task status
    new_tasks = list(task_list)
    new_tasks[idx]["status"] = status
    
    return {
        "accumulated_results": state.get("accumulated_results", []) + [result],
        "task_list": new_tasks,
        "current_task_index": idx + 1,
        "hitl_pending": False
    }
