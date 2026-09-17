import os
import json
from groq import Groq
from dotenv import load_dotenv
from state import AgentState

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY_LLM1"))
MODEL = "openai/gpt-oss-20b"

SYSTEM_PROMPT = """You are a Database Schema Expert. Your goal is to identify the minimum set of tables required to answer a user's question.
Output ONLY a JSON list of table names. No markdown, no explanations.
Example Output: ["users", "orders", "products"]"""

def schema_selector_node(state: AgentState):
    db_schema = state.get("db_schema", {})
    user_input = state.get("contextual_query", "")
    
    # Create a compact catalog of table names and their columns for the selector
    # This avoids sending full metadata for every table if possible, 
    # but still gives the LLM enough info to choose.
    catalog = {}
    for table, details in db_schema.items():
        catalog[table] = list(details.get("columns", {}).keys())

    prompt = f"Database Catalog: {json.dumps(catalog)}\n\nUser Question: {user_input}"

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        temperature=0
    )
    
    try:
        content = response.choices[0].message.content.strip()
        # Clean markdown if present
        if content.startswith("```json"):
            content = content.split("```json")[1].split("```")[0].strip()
        elif content.startswith("```"):
            content = content.split("```")[1].split("```")[0].strip()
            
        selected_tables = json.loads(content)
        
        if not isinstance(selected_tables, list):
            selected_tables = [selected_tables]
            
        # Extract full schema for only the selected tables
        pruned_schema = {table: db_schema[table] for table in selected_tables if table in db_schema}
        
        # Fallback: if nothing selected or error, send full schema to avoid breaking functionality
        if not pruned_schema:
            pruned_schema = db_schema

        return {"selected_schema": pruned_schema}
        
    except Exception as e:
        # Return full schema as fallback to maintain application functionality
        return {"selected_schema": db_schema}
