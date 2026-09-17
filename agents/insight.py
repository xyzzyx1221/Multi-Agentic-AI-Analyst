import os
from groq import Groq
from dotenv import load_dotenv
from state import AgentState

load_dotenv()

# LLM 1 config
client = Groq(api_key=os.getenv("GROQ_API_KEY_LLM1"))
MODEL = "openai/gpt-oss-20b"

SYSTEM_PROMPT = """You are an Insight Generator. Your job is to take the raw results of several SQL queries and the original user request, then synthesize a natural-language answer.
Be concise and direct. If the results are empty or contain errors, explain why.
Do not mention the SQL queries themselves, just the answer."""

def insight_node(state: AgentState):
    results = state.get("accumulated_results", [])
    user_input = state.get("user_input", "")
    
    prompt = f"User Request: {user_input}\n\nSQL Results: {results}"
    
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        temperature=0
    )
    
    final_insight = response.choices[0].message.content
    return {"final_insight": final_insight}
