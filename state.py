from typing import TypedDict, Optional, Literal

class Task(TypedDict):
    task_id: int
    description: str
    status: Literal["pending", "done", "failed"]

class TaskResult(TypedDict):
    task_id: int
    description: str
    sql_query: str
    result: dict | list | str
    error: Optional[str]

class AgentState(TypedDict):
    # Session / identity
    session_id: str
    chat_history_summary: str          # summarized past turns, not full transcript

    # Input processing
    user_input: str
    contextual_query: str              # Recaller Agent output

    # Schema (fetched once, cached, sent in full every time)
    db_schema: dict
    selected_schema: dict  # Pruned schema containing only relevant tables


    # Planning
    task_list: list[Task]
    current_task_index: int

    # Per-task working fields (reset when moving to a new task)
    current_sql_query: str
    guard_keyword: Literal["safe", "ask_before_running", "update"]
    correction_count: int              # per-task, capped at 3
    force_execute: bool                # set True once correction_count hits 3

    # HITL (surfaced in Streamlit)
    hitl_pending: bool
    hitl_payload: Optional[dict]       # {task_id, sql_query, description} shown to user
    hitl_response: Optional[Literal["approve", "reject"]]

    # Aggregation
    accumulated_results: list[TaskResult]

    # Final
    final_insight: str
