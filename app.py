import streamlit as st
import pandas as pd
from pypdf import PdfReader
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
import re
import json
import os
import time
from datetime import datetime

# 1. PAGE CONFIGURATION
st.set_page_config(page_title="Literature Review Buddy", page_icon="📚", layout="wide")

# 2. STORAGE SETUP
DB_FILE = "buddy_projects.json"

def load_data():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f:
                data = json.load(f)
                new_data = {}
                for k, v in data.items():
                    if isinstance(v, list):
                        new_data[k] = {"papers": v, "last_accessed": 0}
                    else:
                        new_data[k] = v
                return new_data
        except:
            return {}
    return {}

def save_data(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=4)

# 3. STYLING
st.markdown("""
<style>
[data-testid="stHeader"] { background-color: rgba(255, 255, 255, 0); }
:root {
    --buddy-green: #18A48C;
    --buddy-blue: #0000FF;
}

[data-testid="block-container"] {
    padding-top: 0rem !important;
    padding-bottom: 2rem !important;
}

/* -------------------------
   GLOBAL HOVER LOGIC
   ------------------------- */
div[data-testid="stButton"] button:hover {
    background-color: var(--buddy-green) !important;
    color: white !important;
    border-color: var(--buddy-green) !important;
}

/* -------------------------
   PINNED BOTTOM-RIGHT DELETE BUTTON
   ------------------------- */
/* Force the container to occupy full width and align items to the end (right) */
.card-del-footer {
    display: flex !important;
    flex-direction: row !important;
    justify-content: flex-end !important;
    width: 100% !important;
    margin-top: 1.5rem !important;
}

/* Target Streamlit's internal button wrapper to prevent it from shrinking to the left */
.card-del-footer div[data-testid="stButton"] {
    margin-left: auto !important;
    display: flex !important;
    justify-content: flex-end !important;
}

.card-del-footer div[data-testid="stButton"] button {
    color: #ff4b4b !important;
    border: 1px solid #ff4b4b !important;
    background: transparent !important;
    font-size: 0.85rem !important;
    height: 34px !important;
    padding: 0 15px !important;
    white-space: nowrap !important;
}

/* -------------------------
   PROJECT PAGE STYLES
   ------------------------- */
.fixed-header-bg {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 4.5rem; 
    background: white;
    border-bottom: 0.125rem solid #f0f2f6;
    z-index: 1000;
    padding-left: 3.75rem;
    display: flex;
    align-items: center;
}

.fixed-header-text h1 { margin: 0; font-size: 2.2rem; color: #0000FF; line-height: 1.1; }

.upload-pull-up {
    margin-top: -3.0rem !important; 
    padding-bottom: 1rem;
}

.bottom-actions {
    margin-top: 1rem;      
    padding-top: 1rem;     
    padding-bottom: 2rem;
    border-top: 0.06rem solid #eee;
}

div[data-testid="stButton"] > button:not([kind="secondary"]) {
    border: 0.06rem solid var(--buddy-green) !important;
    color: var(--buddy-green) !important;
    background: transparent !important;
    font-weight: bold !important;
}

.section-title { font-weight: bold; color: #0000FF; margin-top: 1rem; display: block; text-transform: uppercase; font-size: 0.85rem; border-bottom: 0.06rem solid #eee; }
</style>
""", unsafe_allow_html=True)

# 4. AUTHENTICATION
def check_password():
    correct_password = st.secrets.get("APP_PASSWORD")
    if "password_correct" not in st.session_state:
        st.markdown('<h1>📚 Literature Review Buddy</h1>', unsafe_allow_html=True)
        pwd = st.text_input("Enter password", type="password")
        if st.button("Unlock"):
            if pwd == correct_password:
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("🚫 Access Denied")
        return False
    return True

# 5. MAIN LOGIC
if check_password():
    api_key = st.secrets.get("GEMINI_API_KEY")

    if 'projects' not in st.session_state:
        st.session_state.projects = load_data()
    if 'active_project' not in st.session_state:
        st.session_state.active_project = None 

    if st.session_state.active_project is None:
        # LIBRARY VIEW
        st.markdown('<div><h1 style="margin:0; font-size: 2.5rem; color:#0000FF;">🗂️ Project Library</h1><p style="color:#18A48C; font-weight: bold; font-size: 1.1rem; margin-bottom: 1.25rem;">Select an existing review or start a new one.</p></div>', unsafe_allow_html=True)
        # (Library logic omitted for brevity, same as previous)
        # ... (Include library code here) ...
    else:
        # PROJECT VIEW
        st.markdown(f'<div class="fixed-header-bg"><div class="fixed-header-text"><h1>{st.session_state.active_project}</h1></div></div>', unsafe_allow_html=True)
        st.markdown('<div class="upload-pull-up">', unsafe_allow_html=True)
        llm = None
        if api_key: llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", google_api_key=api_key, temperature=0.1)
        uploaded_files = st.file_uploader("Upload academic papers (PDF)", type="pdf", accept_multiple_files=True)
        run_review = st.button("🔬 Analyse paper", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

        papers_data = st.session_state.projects[st.session_state.active_project]["papers"]
        if papers_data:
            t1, t2, t3 = st.tabs(["🖼️ Individual Papers", "📊 Master Table", "🧠 Synthesis"])
            with t1:
                for idx, r in enumerate(reversed(papers_data)):
                    real_idx = len(papers_data) - 1 - idx
                    with st.container(border=True):
                        col_metric, col_title = st.columns([1, 14])
                        with col_metric: st.metric("Ref", r['#'])
                        with col_title: st.subheader(r['Title'])
                        
                        st.markdown(f'<div><b>Authors:</b> {r["Authors"]}<br><b>Year:</b> {r["Year"]}<br><b>Citation:</b> {r["Reference"]}</div>', unsafe_allow_html=True)
                        st.divider()
                        
                        sec = [("📝 Summary", r["Summary"]), ("💡 Findings", r["Findings"])] # Truncated for example
                        for k, v in sec: st.markdown(f'**{k}**: {v}')
                        
                        # THE PINNED FOOTER
                        st.markdown('<div class="card-del-footer">', unsafe_allow_html=True)
                        if st.button("🗑️ Delete Paper", key=f"del_paper_{real_idx}"):
                            st.session_state.projects[st.session_state.active_project]["papers"].pop(real_idx)
                            for i, p in enumerate(st.session_state.projects[st.session_state.active_project]["papers"]): p["#"] = i + 1
                            save_data(st.session_state.projects)
                            st.rerun()
                        st.markdown('</div>', unsafe_allow_html=True)
            # ... (Other tabs) ...

        st.markdown('<div class="bottom-actions">', unsafe_allow_html=True)
        f1, f2, f3 = st.columns([6, 1, 1])
        with f2: st.button("💾 Save", key="final_save", use_container_width=True)
        with f3: 
            if st.button("🏠 Library", key="final_lib", use_container_width=True):
                st.session_state.active_project = None
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
