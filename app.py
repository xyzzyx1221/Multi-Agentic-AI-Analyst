import streamlit as st
import uuid
from graph import create_graph
from db import fetch_db_schema
from langgraph.constants import Command
from auth import create_user, login_user, get_user_quota, increment_user_quota

st.set_page_config(page_title="Multi Agent AI Analyst", page_icon="🤖", layout="wide")

# Initialize the graph in session state to avoid re-creating it on every rerun
if 'app_graph' not in st.session_state:
    st.session_state.app_graph = create_graph()
app_graph = st.session_state.app_graph


# --- Authentication State ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user_id" not in st.session_state:
    st.session_state.user_id = None

# --- Login / Signup UI ---
if not st.session_state.authenticated:
    # Custom CSS for a better login experience
    st.markdown("""
        <style>
        .main {
            background-color: #f5f7f9;
        }
        .stButton>button {
            width: 100%;
            border-radius: 5px;
            height: 3em;
            background-color: #ff4b4b;
            color white;
        }
        .login-container {
            max-width: 400px;
            margin: 0 auto;
            padding: 2rem;
            background-color: white;
            border-radius: 15px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }
        </style>
    """, unsafe_allow_html=True)

    # Center the login box
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<h1 style='text-align: center;'>🔐 Welcome to AI Analyst</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: gray;'>Please sign in to access your database insights</p>", unsafe_allow_html=True)
        
        tab1, tab2 = st.tabs(["Login", "Sign Up"])
        
        with tab1:
            with st.form("login_form"):
                l_user = st.text_input("Username/Email")
                l_pass = st.text_input("Password", type="password")
                if st.form_submit_button("Login"):
                    uid = login_user(l_user, l_pass)
                    if uid:
                        st.session_state.authenticated = True
                        st.session_state.user_id = uid
                        st.rerun()
                    else:
                        st.error("Invalid username or password")
                        
        with tab2:
            with st.form("signup_form"):
                s_user = st.text_input("Email Address")
                s_pass = st.text_input("Choose Password", type="password")
                if st.form_submit_button("Create Account"):
                    if "@" not in s_user or "." not in s_user:
                        st.error("Please enter a valid email address.")
                    elif not s_pass:
                        st.error("Password cannot be empty.")
                    else:
                        uid = create_user(s_user, s_pass)
                        if uid:
                            st.success("Account created! Please login.")
                        else:
                            st.error("Email already exists or error occurred.")
    st.stop()

# --- Main Application ---
st.title("🤖 Multi Agent AI Analyst")
st.markdown("### Chat with your database")
st.info("📝 **Note:** This application uses in-memory session storage. Refreshing the page or restarting the server will clear all current chat history. To optimize costs, only the most recent turn is maintained in context.")

# --- Sidebar ---
with st.sidebar:
    st.header("👤 User Profile")
    st.write(f"User ID: {st.session_state.user_id}")
    
    # Quota Display
    current_quota = get_user_quota(st.session_state.user_id)
    st.metric("Queries Used", f"{current_quota} / 5")
    
    if st.button("Logout"):
        st.session_state.authenticated = False
        st.session_state.user_id = None
        st.rerun()

    st.divider()
    st.header("🛠️ Tool Capabilities")
    st.markdown("""
    **Key Features:**
    - 🧠 **Multi-Agent Orchestration**: Specialized agents for recalling, planning, generating, and guarding.
    - 🛡️ **Built-in Guardrails**: Every query is validated for security and correctness before execution.
    - 👤 **Human-In-The-Loop (HITL)**: You approve sensitive modifications before they hit your database.
    - 📊 **Refined SQL**: Converts plain English into optimized PostgreSQL queries based on your real schema.
    - 💾 **STM Context**: Uses Short-Term Memory (STM) to maintain context-based chatting.
    """)
    
    st.divider()
    with st.expander("👨‍💻 About the Developer"):
        st.markdown("""
        **Ranveer Raj**  
        National Institute of Technology Raipur
        """)
    
    st.divider()
    st.header("💡 Suggested Prompts")
    suggestions = [
        "How many customers are there in total?",
        "Who are the top 10 customers by total spending?",
        "What is the total revenue for the last month?",
        "Show me the product categories with the highest returns.",
        "Insert a new customer named 'Acme Corp' from 'New York'"
    ]
    for suggestion in suggestions:
        if st.button(suggestion):
            st.session_state.pending_prompt = suggestion
            st.rerun()

# --- Session State Initialization ---
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if "messages" not in st.session_state:
    st.session_state.messages = []

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "pending_prompt" not in st.session_state:
    st.session_state.pending_prompt = None

# Get schema once and store in session
if "db_schema" not in st.session_state:
    with st.spinner("Fetching database schema..."):
        st.session_state.db_schema = fetch_db_schema()

thread_config = {"configurable": {"thread_id": st.session_state.session_id}}

# --- Display Chat History ---
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# --- HITL & State Management ---
state = app_graph.get_state(thread_config)
hitl_active = False

if state.next:
    interrupt_payload = None
    if state.tasks:
        for task in state.tasks:
            if task.interrupts:
                interrupt_payload = task.interrupts[0].value
                break
    
    if interrupt_payload:
        hitl_active = True
        with st.chat_message("assistant"):
            st.warning("⚠️ **Action Required: SQL Approval**")
            desc = interrupt_payload.get('description', 'No description provided')
            sql = interrupt_payload.get('sql_query', 'No SQL provided')
            
            st.info(f"**Task:** {desc}")
            st.code(sql, language="sql")
            
            col1, col2 = st.columns(2)
            if col1.button("✅ Approve", use_container_width=True):
                app_graph.invoke(Command(resume="approve"), config=thread_config)
                st.rerun()
            if col2.button("❌ Reject", use_container_width=True):
                app_graph.invoke(Command(resume="reject"), config=thread_config)
                st.rerun()

# --- User Interaction ---
current_prompt = None
if st.session_state.get("pending_prompt"):
    current_prompt = st.session_state.pending_prompt
    st.session_state.pending_prompt = None

prompt = st.chat_input("Ask your database...") or current_prompt

if prompt:
    # --- QUOTA CHECK ---
    user_quota = get_user_quota(st.session_state.user_id)
    if user_quota >= 5:
        st.error("❌ You have reached your limit of 5 queries. Please contact the administrator.")
        st.stop()

    # --- FULL STATE RESET FOR NEW QUERY ---
    try:
        state_check = app_graph.get_state(thread_config)
        if state_check.next:
            app_graph.invoke(Command(resume="reject"), config=thread_config)
    except Exception:
        pass
    
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("🤖 AI Analyst is thinking..."):
            recent_history = st.session_state.chat_history[-2:]
            history_text = "\n".join([f"{m['role']}: {m['content']}" for m in recent_history])
            
            # Construct the initial state for the graph
            inputs = {
                "user_input": prompt,
                "session_id": st.session_state.session_id,
                "db_schema": st.session_state.db_schema,
                "chat_history_summary": history_text,
                "accumulated_results": [],
                "task_list": [],
                "current_task_index": 0,
                "correction_count": 0,
                "force_execute": False,
                "hitl_pending": False
            }

            
            try:
                final_state = app_graph.invoke(inputs, config=thread_config)
                
                current_state = app_graph.get_state(thread_config)
                if not current_state.next and "final_insight" in final_state:
                    response = final_state["final_insight"]
                    st.markdown(response)
                    st.session_state.messages.append({"role": "assistant", "content": response})
                    st.session_state.chat_history.append({"role": "user", "content": prompt})
                    st.session_state.chat_history.append({"role": "assistant", "content": response})
                    
                    # Increment quota on success
                    increment_user_quota(st.session_state.user_id)
                elif current_state.next:
                    st.info("Query paused for approval. Please check the approval panel above.")
                    st.rerun()
            except Exception as e:
                st.error(f"An error occurred while processing your request: {e}")
                try:
                    app_graph.invoke(Command(resume="reject"), config=thread_config)
                except:
                    pass
