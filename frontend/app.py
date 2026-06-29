"""
frontend/app.py
────────────────
Streamlit frontend for the Loan Advisory Agent.

Design intent: dark professional finance aesthetic — deep navy palette,
clean monospace data readouts, confidence badges, and source attribution.
Think Bloomberg terminal meets modern chat UI.

Run:
  streamlit run frontend/app.py

Requires backend running at: http://localhost:8000
"""

import uuid
import httpx
import streamlit as st

# ── Page config (MUST be first Streamlit call) ────────────────────────────────
st.set_page_config(
    page_title="Loan Advisory Agent",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS — dark finance theme ───────────────────────────────────────────
st.markdown("""
<style>
  /* Base */
  .stApp { background-color: #0d1117; color: #e6edf3; font-family: 'Inter', sans-serif; }
  
  /* Sidebar */
  [data-testid="stSidebar"] { background-color: #161b22; border-right: 1px solid #21262d; }
  [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
    color: #58a6ff; }

  /* Chat messages */
  .user-msg {
    background: #1c2128; border-left: 3px solid #58a6ff;
    padding: 12px 16px; border-radius: 6px; margin: 8px 0; }
  .agent-msg {
    background: #161b22; border-left: 3px solid #3fb950;
    padding: 12px 16px; border-radius: 6px; margin: 8px 0; }
  .agent-msg code { background: #0d1117; color: #79c0ff; }

  /* Confidence badge */
  .badge-high   { background:#1a4731; color:#3fb950; padding:2px 10px; border-radius:12px; font-size:12px; font-weight:600; }
  .badge-medium { background:#3d2600; color:#e3b341; padding:2px 10px; border-radius:12px; font-size:12px; font-weight:600; }
  .badge-low    { background:#3d0014; color:#f85149; padding:2px 10px; border-radius:12px; font-size:12px; font-weight:600; }

  /* Source chips */
  .source-chip {
    display:inline-block; background:#21262d; color:#8b949e;
    padding:2px 10px; border-radius:12px; font-size:11px;
    margin:2px; border:1px solid #30363d; }

  /* Metric cards */
  .metric-card {
    background:#161b22; border:1px solid #21262d;
    border-radius:8px; padding:12px; margin:4px 0; }
  .metric-label { color:#8b949e; font-size:11px; text-transform:uppercase; letter-spacing:0.8px; }
  .metric-value { color:#e6edf3; font-size:20px; font-weight:700; margin-top:2px; }

  /* Input box */
  .stTextInput > div > div > input {
    background:#161b22; border:1px solid #30363d; color:#e6edf3; border-radius:6px; }
  .stTextInput > div > div > input:focus { border-color:#58a6ff; }

  /* Buttons */
  .stButton > button {
    background:#238636; color:#fff; border:none; border-radius:6px;
    font-weight:600; padding:8px 20px; }
  .stButton > button:hover { background:#2ea043; }

  /* Divider */
  hr { border-color: #21262d; }
  
  /* Hide Streamlit branding */
  #MainMenu, footer, header { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

BACKEND_URL = "http://localhost:8000"

# ── Session state init ─────────────────────────────────────────────────────────
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "messages" not in st.session_state:
    st.session_state.messages = []
if "selected_applicant" not in st.session_state:
    st.session_state.selected_applicant = None


# ── Helpers ───────────────────────────────────────────────────────────────────

def confidence_badge(score: float) -> str:
    pct = int(score * 100)
    if score >= 0.7:
        return f'<span class="badge-high">● {pct}% Confidence</span>'
    elif score >= 0.45:
        return f'<span class="badge-medium">● {pct}% Confidence</span>'
    return f'<span class="badge-low">● {pct}% Confidence</span>'


def source_chips(sources: list[str]) -> str:
    if not sources:
        return ""
    chips = " ".join(f'<span class="source-chip">📄 {s}</span>' for s in sources)
    return f"<div style='margin-top:8px'>{chips}</div>"


def query_agent(query: str, applicant_id: str | None = None) -> dict:
    """Send query to FastAPI backend."""
    try:
        with httpx.Client(timeout=60) as client:
            r = client.post(f"{BACKEND_URL}/api/chat", json={
                "query": query,
                "session_id": st.session_state.session_id,
                "applicant_id": applicant_id,
            })
            r.raise_for_status()
            return r.json()
    except httpx.ConnectError:
        return {
            "response": "⚠️ Cannot connect to backend. Is the FastAPI server running?\n\n"
                        "Start it with: `uvicorn backend.main:app --reload`",
            "sources": [], "confidence_score": 0.0,
            "agent_metadata": None, "error": "Connection refused",
        }
    except Exception as e:
        return {
            "response": f"⚠️ Error: {e}",
            "sources": [], "confidence_score": 0.0,
            "agent_metadata": None, "error": str(e),
        }


def fetch_applicants() -> list[dict]:
    try:
        with httpx.Client(timeout=10) as client:
            r = client.get(f"{BACKEND_URL}/api/applicants")
            return r.json().get("applicants", [])
    except Exception:
        return []


# ── SIDEBAR ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## 🏦 Loan Advisory Agent")
    st.markdown(
        "<small style='color:#8b949e'>Powered by LangGraph · RAG · GPT-4o</small>",
        unsafe_allow_html=True,
    )
    st.divider()

    # Applicant selector
    st.markdown("### 👤 Applicant Context")
    st.markdown(
        "<small style='color:#8b949e'>Optional — for eligibility & fraud queries</small>",
        unsafe_allow_html=True,
    )
    
    applicants = fetch_applicants()
    applicant_options = {"— None (policy query) —": None}
    applicant_options.update({
        f"{a['full_name']} ({a['city']})": a["id"] for a in applicants
    })

    selected_label = st.selectbox(
        "Select applicant",
        options=list(applicant_options.keys()),
        label_visibility="collapsed",
    )
    applicant_id = applicant_options[selected_label]
    st.session_state.selected_applicant = applicant_id

    # Show applicant quick stats if selected
    if applicant_id and applicants:
        appl = next((a for a in applicants if a["id"] == applicant_id), None)
        if appl:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.markdown(f'<div class="metric-label">Monthly Income</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="metric-value">₹{appl["monthly_income"]:,.0f}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="metric-label" style="margin-top:8px">Employment</div>', unsafe_allow_html=True)
            st.markdown(f'<div style="color:#e6edf3;font-size:13px">{appl["employment_type"].replace("_", " ").title()}</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

    st.divider()

    # Session controls
    st.markdown("### ⚙️ Session")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 New Chat", use_container_width=True):
            st.session_state.messages = []
            st.session_state.session_id = str(uuid.uuid4())
            st.rerun()
    with col2:
        st.markdown(
            f"<small style='color:#8b949e'>ID: {st.session_state.session_id[:8]}...</small>",
            unsafe_allow_html=True,
        )

    st.divider()

    # Quick prompts
    st.markdown("### 💡 Try These Queries")
    quick_prompts = [
        "What is the minimum credit score for a home loan?",
        "Calculate EMI for ₹50 lakh at 8.5% for 20 years",
        "What documents are required for a personal loan?",
        "Am I eligible for a home loan?",
        "What is the maximum loan amount I can get?",
        "Explain the debt-to-income ratio limit",
    ]
    for prompt in quick_prompts:
        if st.button(prompt, key=f"prompt_{prompt[:20]}", use_container_width=True):
            st.session_state.pending_query = prompt
            st.rerun()

    st.divider()
    st.markdown(
        "<small style='color:#484f58'>This is a prototype using synthetic data. "
        "Not financial advice.</small>",
        unsafe_allow_html=True,
    )


# ── MAIN PANEL ────────────────────────────────────────────────────────────────

st.markdown(
    "<h1 style='color:#e6edf3; margin-bottom:4px'>Loan Advisory Agent</h1>"
    "<p style='color:#8b949e; margin-top:0'>Ask anything about loan eligibility, EMI, and policy guidelines.</p>",
    unsafe_allow_html=True,
)
st.divider()

# Chat history display
chat_container = st.container()
with chat_container:
    for msg in st.session_state.messages:
        if msg["role"] == "user":
            st.markdown(
                f'<div class="user-msg"><strong style="color:#58a6ff">You</strong><br>{msg["content"]}</div>',
                unsafe_allow_html=True,
            )
        else:
            meta = msg.get("metadata", {})
            badge = confidence_badge(meta.get("confidence_score", 0))
            chips = source_chips(msg.get("sources", []))

            st.markdown(
                f'<div class="agent-msg">'
                f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">'
                f'<strong style="color:#3fb950">🤖 Agent</strong>'
                f'{badge}'
                f'</div>'
                f'{msg["content"]}'
                f'{chips}'
                f'</div>',
                unsafe_allow_html=True,
            )

            # Agent metadata expander (debug panel)
            if meta and meta.get("query_type"):
                with st.expander("🔍 Agent Pipeline Details", expanded=False):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Query Type", meta.get("query_type", "—").title())
                    with col2:
                        st.metric("Hallucination Risk", meta.get("hallucination_risk", "—").title())
                    with col3:
                        st.metric("Fallback", "Yes" if meta.get("fallback_triggered") else "No")

                    agents = meta.get("agents_invoked", [])
                    if agents:
                        st.markdown(f"**Agents invoked:** {' → '.join(a.replace('_', ' ').title() for a in agents)}")

# ── INPUT ─────────────────────────────────────────────────────────────────────
st.divider()

# Handle quick prompt injection
pending = st.session_state.pop("pending_query", None)

with st.form("chat_form", clear_on_submit=True):
    col_input, col_btn = st.columns([5, 1])
    with col_input:
        user_input = st.text_input(
            "Ask a loan question...",
            value=pending or "",
            placeholder="e.g. What is the EMI for a ₹30 lakh home loan at 8.5% for 20 years?",
            label_visibility="collapsed",
        )
    with col_btn:
        submitted = st.form_submit_button("Send →", use_container_width=True)

if submitted and user_input.strip():
    query = user_input.strip()

    # Add user message
    st.session_state.messages.append({"role": "user", "content": query})

    # Query agent with spinner
    with st.spinner("Agent pipeline running..."):
        response_data = query_agent(query, applicant_id=st.session_state.selected_applicant)

    # Add agent response
    st.session_state.messages.append({
        "role": "assistant",
        "content": response_data.get("response", "No response received."),
        "sources": response_data.get("sources", []),
        "metadata": response_data.get("agent_metadata") or {},
    })

    st.rerun()