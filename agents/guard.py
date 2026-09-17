import os
import json
from groq import Groq
from dotenv import load_dotenv
from state import AgentState

load_dotenv()

# LLM 1 config
client = Groq(api_key=os.getenv("GROQ_API_KEY_LLM1"))
MODEL = "openai/gpt-oss-20b"

SYSTEM_PROMPT = """You are a SQL Guard Agent. Your job is to validate a generated SQL query against the database schema.
You must classify the query into one of these three keywords based on these STRICT rules:

1. 'update' $\rightarrow$ Use this if the query is syntactically incorrect, logically flawed, or if the SQL query does not match the intended task description. This triggers a regeneration loop.
2. 'ask_before_running' $\rightarrow$ Use this ONLY for queries that modify the database content (e.g., INSERT, UPDATE, DELETE, DROP, TRUNCATE). This triggers Human-In-The-Loop approval.
3. 'safe' $\rightarrow$ Use this for all correct SELECT queries that only read data and match the task.

Return ONLY a JSON object with the key 'guard_keyword'.
Example: {"guard_keyword": "safe"}
Only output valid JSON."""

def guard_node(state: AgentState):
    sql_query = state.get("current_sql_query", "")
    db_schema = state.get("db_schema", {})
    
    prompt = f"Schema: {json.dumps(db_schema)}\n\nSQL Query: {sql_query}"
    
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
        data = json.loads(response.choices[0].message.content)
        keyword = data.get("guard_keyword", "update")
        
        # Increment correction count if we are asking for an update
        current_count = state.get("correction_count", 0)
        new_count = current_count + 1 if keyword == "update" else current_count
        
        return {"guard_keyword": keyword, "correction_count": new_count}
    except Exception:
        return {"guard_keyword": "update", "correction_count": state.get("correction_count", 0) + 1}
