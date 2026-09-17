from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from state import AgentState
from agents.recaller import recaller_node
from agents.planner import planner_node
from agents.schema_selector import schema_selector_node
from agents.sql_generator import sql_generator_node
from agents.guard import guard_node

from agents.executor import executor_node
from agents.insight import insight_node
from db import fetch_db_schema

def create_graph():
    workflow = StateGraph(AgentState)

    # Add Nodes
    workflow.add_node("recaller", recaller_node)
    workflow.add_node("planner", planner_node)
    workflow.add_node("schema_selector", schema_selector_node)
    workflow.add_node("sql_generator", sql_generator_node)
    workflow.add_node("guard", guard_node)

    workflow.add_node("executor", executor_node)
    workflow.add_node("insight", insight_node)

    # Build Graph
    workflow.set_entry_point("recaller")
    workflow.add_edge("recaller", "schema_selector")
    workflow.add_edge("schema_selector", "planner")
    workflow.add_edge("planner", "sql_generator")
    workflow.add_edge("sql_generator", "guard")


    
    # Correction Loop Logic
    def route_guard(state: AgentState):
        if state.get("guard_keyword") == "update":
            if state.get("correction_count", 0) >= 3:
                return "force_execute"
            return "sql_generator"
        return "executor"

    workflow.add_conditional_edges(
        "guard",
        route_guard,
        {
            "sql_generator": "sql_generator",
            "executor": "executor",
            "force_execute": "executor"
        }
    )

    # Task Loop Logic
    def route_executor(state: AgentState):
        idx = state.get("current_task_index", 0)
        tasks = state.get("task_list", [])
        if idx < len(tasks):
            return "next_task"
        return "finish"

    workflow.add_conditional_edges(
        "executor",
        route_executor,
        {
            "next_task": "sql_generator",
            "finish": "insight"
        }
    )

    workflow.add_edge("insight", END)

    # For force_execute, we need a simple node or logic to set the flag
    # Since route_guard can just return "executor", we can handle force_execute inside executor_node
    # However, let's add a small wrapper to set the force_execute flag if needed
    def set_force_execute(state: AgentState):
        return {"force_execute": True}
    
    workflow.add_node("set_force_execute", set_force_execute)
    workflow.add_edge("set_force_execute", "executor")
    
    # Update route_guard to use set_force_execute
    def route_guard_v2(state: AgentState):
        if state.get("guard_keyword") == "update":
            if state.get("correction_count", 0) >= 3:
                return "set_force_execute"
            return "sql_generator"
        return "executor"
    
    # We need to redefine the conditional edge because we changed the logic
    workflow.add_conditional_edges(
        "guard",
        route_guard_v2,
        {
            "sql_generator": "sql_generator",
            "executor": "executor",
            "set_force_execute": "set_force_execute"
        }
    )

    # Checkpointer for session-based persistence
    memory = MemorySaver()
    return workflow.compile(checkpointer=memory)

# Global instance to be reused by Streamlit
app_graph = create_graph()
