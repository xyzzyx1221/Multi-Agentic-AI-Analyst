import os
from groq import Groq
from dotenv import load_dotenv
from state import AgentState

load_dotenv()

# LLM 2 config
client = Groq(api_key=os.getenv("GROQ_API_KEY_LLM2"))
MODEL = "openai/gpt-oss-120b"

SYSTEM_PROMPT = """You are a Context Recaller. Your job is to merge the user's new input with the summarized chat history into a single, self-contained, context-resolved query. 
Resolve all pronouns (e.g., 'that table', 'the previous result', 'it') into explicit entities based on the history.
Output only the resolved query, no preamble."""

def recaller_node(state: AgentState):
    user_input = state.get("user_input", "")
    history = state.get("chat_history_summary", "")
    
    prompt = f"History: {history}\n\nUser Input: {user_input}"
    
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        temperature=0
    )
    
    contextual_query = response.choices[0].message.content
    return {"contextual_query": contextual_query}
