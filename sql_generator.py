import os
import json
from groq import Groq
from dotenv import load_dotenv
from state import AgentState

load_dotenv()

# LLM 1 config
client = Groq(api_key=os.getenv("GROQ_API_KEY_LLM1"))
MODEL = "openai/gpt-oss-20b"

SYSTEM_PROMPT = """You are a precise SQL Generator. Your job is to write a valid SQL query based on the task description and database schema.
Output ONLY the SQL query. No markdown blocks, no explanations, no comments.
Ensure the SQL is compatible with PostgreSQL."""

def sql_generator_node(state: AgentState):
    task_list = state.get("task_list", [])
    idx = state.get("current_task_index", 0)
    full_schema = state.get("db_schema", {})
    
    if idx >= len(task_list):
        return {}

    task = task_list[idx]
    
    # Token Optimization: Filter schema based on Planner's required tables
    required_tables = task.get("required_tables", [])
    if required_tables:
        # Filter the schema to include only tables mentioned by the planner
        filtered_schema = [table for table in full_schema if table.get("name") in required_tables]
    else:
        # Fallback to full schema if planner didn't specify
        filtered_schema = full_schema
    
    # Check if this is a correction pass
    previous_sql = state.get("current_sql_query")
    
    prompt = f"Schema: {json.dumps(filtered_schema)}\n\nTask: {task['description']}"
    if previous_sql:
        prompt += f"\n\nPrevious Attempt (Rejected): {previous_sql}\nCorrect it based on the rules."

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        temperature=0
    )
    
    sql_query = response.choices[0].message.content.strip()
    # Clean up any markdown formatting just in case
    if sql_query.startswith("```sql"):
        sql_query = sql_query.split("```sql")[1].split("```")[0].strip()
    elif sql_query.startswith("```"):
        sql_query = sql_query.split("```")[1].split("```")[0].strip()

    return {"current_sql_query": sql_query}
