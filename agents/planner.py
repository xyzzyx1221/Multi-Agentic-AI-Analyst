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
Each task should be a plain-English instruction for a SQL generator.
Return the result as a JSON object with a key 'tasks' containing a list of objects with 'task_id' and 'description'.

Example output:
{
  "tasks": [
    {"task_id": 1, "description": "Get the total number of users from the users table"},
    {"task_id": 2, "description": "Get the top 5 users by order count from the orders table"}
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
            
        # Ensure status is added
        task_list = []
        for t in tasks:
            task_list.append({
                "task_id": t["task_id"],
                "description": t["description"],
                "status": "pending"
            })
            
        return {"task_list": task_list, "current_task_index": 0}
    except Exception as e:
        # Fallback: create a single task from the query if planning fails
        return {
            "task_list": [{"task_id": 1, "description": contextual_query, "status": "pending"}],
            "current_task_index": 0
        }
