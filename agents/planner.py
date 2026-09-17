import os
import json
from groq import Groq
from dotenv import load_dotenv
from state import AgentState, Task

load_dotenv()

# LLM 2 config
client = Groq(api_key=os.getenv("GROQ_API_KEY_LLM2"))
MODEL = "openai/gpt-oss-120b"

SYSTEM_PROMPT = """You are a SQL Planner. Based on the user's contextual query and the database schema, break the request down into a sequence of independent SQL tasks.

For each task, you MUST identify the specific tables and columns required to complete it. Be over-inclusive: if you are unsure if a table or column is needed, include it to ensure the SQL generator has all necessary context.

Return the result as a JSON object with a key 'tasks' containing a list of objects with:
- 'task_id': (int)
- 'description': (string) Plain-English instruction for the SQL generator.
- 'required_tables': (list of strings) Exact names of tables needed.
- 'required_columns': (list of strings) Specific columns needed (optional but recommended).

Example output:
{
  "tasks": [
    {
      "task_id": 1, 
      "description": "Get the total number of users", 
      "required_tables": ["users"], 
      "required_columns": ["user_id"]
    },
    {
      "task_id": 2, 
      "description": "Get the top 5 users by order count", 
      "required_tables": ["users", "orders"], 
      "required_columns": ["users.user_id", "users.username", "orders.user_id"]
    }
  ]
}
Only output valid JSON."""

def planner_node(state: AgentState):
    contextual_query = state.get("contextual_query", "")
    db_schema = state.get("db_schema", {})
    
    prompt = f"Schema: {json.dumps(db_schema)}\n\nQuery: {contextual_query}"
    
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        temperature=0,
        response_format={"type": "json_object"}
    )
    
    try:
        # The model might wrap the list in an object or return a raw list
        content = response.choices[0].message.content
        data = json.loads(content)
        if isinstance(data, dict):
            # Handle cases where model returns {"tasks": [...]}
            tasks = data.get("tasks", data.get("task_list", []))
            if not tasks and isinstance(next(iter(data.values())), list):
                tasks = next(iter(data.values()))
        else:
            tasks = data
            
        # Ensure status and required fields are added
        task_list = []
        for t in tasks:
            if isinstance(t, str):
                # Handle cases where the LLM returns a list of strings instead of objects
                task_list.append({
                    "task_id": len(task_list) + 1,
                    "description": t,
                    "required_tables": [],
                    "required_columns": [],
                    "status": "pending"
                })
            elif isinstance(t, dict):
                task_list.append({
                    "task_id": t.get("task_id", len(task_list) + 1),
                    "description": t.get("description", "No description"),
                    "required_tables": t.get("required_tables", []),
                    "required_columns": t.get("required_columns", []),
                    "status": "pending"
                })
            
        return {"task_list": task_list, "current_task_index": 0}
    except Exception as e:
        # Fallback: create a single task from the query if planning fails
        return {
            "task_list": [{
                "task_id": 1, 
                "description": contextual_query, 
                "required_tables": [], 
                "required_columns": [], 
                "status": "pending"
            }],
            "current_task_index": 0
        }
