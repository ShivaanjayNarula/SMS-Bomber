# pyrefly: ignore [missing-import]
import streamlit as st
import threading
import time
import queue
import collections
import sms_bomber

# ==========================================
# THREAD & QUEUE SETUP
# ==========================================
# We use globals here to bridge the background thread with Streamlit's render thread.
if "LOG_QUEUE" not in st.session_state:
    st.session_state.LOG_QUEUE = queue.Queue()
if "LOG_HISTORY" not in st.session_state:
    st.session_state.LOG_HISTORY = collections.deque(maxlen=200)

if "PROGRESS_STATE" not in st.session_state:
    st.session_state.PROGRESS_STATE = {
        "completed": 0,
        "total": 0,
        "success": 0,
    }

def ui_callback(msg):
    # This runs in the background thread. We push to a queue.
    st.session_state.LOG_QUEUE.put(msg)

def progress_callback(completed, total, success):
    # This runs in the background thread.
    st.session_state.PROGRESS_STATE["completed"] = completed
    st.session_state.PROGRESS_STATE["total"] = total
    st.session_state.PROGRESS_STATE["success"] = success

sms_bomber.UI_CALLBACK = ui_callback
sms_bomber.PROGRESS_CALLBACK = progress_callback

# ==========================================
# STREAMLIT UI CONFIGURATION
# ==========================================
st.set_page_config(
    page_title="Cross-Platform SMS Bomber",
    page_icon="💣",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Dark aesthetic styling
st.markdown("""
<style>
    /* Main Background & Font */
    .stApp {
        background-color: #0e1117;
        color: #fafafa;
        font-family: 'Inter', sans-serif;
    }
    
    /* Buttons */
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        background: linear-gradient(135deg, #ff4b4b 0%, #ff0000 100%);
        color: white;
        font-weight: 600;
        border: none;
        padding: 0.5rem 1rem;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(255, 75, 75, 0.4);
        color: white;
    }
    .stButton>button:active {
        transform: translateY(0px);
    }
    
    /* Console Output */
    .console-box {
        background-color: #1a1c24;
        color: #4ade80;
        font-family: 'Fira Code', monospace;
        font-size: 0.85rem;
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid #2d3748;
        height: 400px;
        overflow-y: auto;
        white-space: pre-wrap;
        box-shadow: inset 0 2px 4px rgba(0,0,0,0.2);
    }
    
    /* Headers */
    h1, h2, h3 {
        background: -webkit-linear-gradient(#fff, #a0aec0);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    /* Metrics */
    div[data-testid="metric-container"] {
        background-color: #1a1c24;
        border: 1px solid #2d3748;
        padding: 1rem;
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)


# ==========================================
# SIDEBAR CONFIGURATION
# ==========================================
with st.sidebar:
    st.title("⚙️ Configuration")
    st.markdown("Configure the parameters for the SMS attack.")
    
    phone_number = st.text_input("Target Phone Number", value="1234567890", max_chars=15)
    batch_size = st.number_input("Batch Size", min_value=1, max_value=200, value=40)
    number_of_batches = st.number_input("Number of Batches", min_value=1, max_value=20, value=3)
    max_concurrent = st.slider("Max Concurrent Browsers", min_value=1, max_value=16, value=8)
    cooldown = st.slider("Batch Cooldown (seconds)", min_value=10, max_value=300, value=(90, 120))
    
    st.divider()
    
    if "is_running" not in st.session_state:
        st.session_state.is_running = False

    if not st.session_state.is_running:
        if st.button("🚀 Start Attack"):
            if len(phone_number) < 10:
                st.error("Please enter a valid phone number.")
            else:
                # Update module variables
                sms_bomber.PHONE_NUMBER = phone_number
                sms_bomber.BATCH_SIZE = batch_size
                sms_bomber.NUMBER_OF_BATCHES = number_of_batches
                sms_bomber.MAX_CONCURRENT_BROWSERS = max_concurrent
                sms_bomber.BATCH_COOLDOWN = cooldown
                sms_bomber.IS_RUNNING = True
                
                # Reset UI states
                st.session_state.LOG_HISTORY.clear()
                while not st.session_state.LOG_QUEUE.empty():
                    st.session_state.LOG_QUEUE.get()
                st.session_state.PROGRESS_STATE = {"completed": 0, "total": 0, "success": 0}
                st.session_state.is_running = True
                
                # Start Thread
                def run_bomber():
                    try:
                        sms_bomber.send_sms_bombs()
                    finally:
                        # Once done, update flag (we can't trigger rerun directly from thread easily,
                        # but the polling loop will catch it)
                        sms_bomber.IS_RUNNING = False
                        st.session_state.LOG_QUEUE.put("=== ATTACK FINISHED ===")
                        
                t = threading.Thread(target=run_bomber, daemon=True)
                t.start()
                st.rerun()
    else:
        if st.button("🛑 Stop Attack"):
            sms_bomber.IS_RUNNING = False
            st.session_state.is_running = False
            st.session_state.LOG_QUEUE.put("[!] Sent stop signal to the threads...")
            st.rerun()

# ==========================================
# MAIN DASHBOARD
# ==========================================
st.title("💣 SMS Bomber Dashboard")
st.markdown("A highly concurrent cross-platform SMS tool powered by undetected_chromedriver.")

# Process logs from queue
while not st.session_state.LOG_QUEUE.empty():
    msg = st.session_state.LOG_QUEUE.get()
    if msg == "=== ATTACK FINISHED ===":
        st.session_state.is_running = False
    else:
        st.session_state.LOG_HISTORY.append(msg)

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Status", "🟢 RUNNING" if st.session_state.is_running else "🔴 STOPPED")
with col2:
    st.metric("Success", f"{st.session_state.PROGRESS_STATE['success']}")
with col3:
    completed = st.session_state.PROGRESS_STATE['completed']
    total = st.session_state.PROGRESS_STATE['total']
    prog_text = f"{completed} / {total}" if total > 0 else "0 / 0"
    st.metric("Current Batch Progress", prog_text)

# Progress bar
if total > 0:
    st.progress(completed / total)
else:
    st.progress(0.0)

st.subheader("Live Console")
logs_text = "\n".join(st.session_state.LOG_HISTORY)

# The console box is rendered as raw HTML
st.markdown(f'<div class="console-box">{logs_text}</div>', unsafe_allow_html=True)

# Polling mechanism
if st.session_state.is_running:
    time.sleep(1.0)
    st.rerun()
