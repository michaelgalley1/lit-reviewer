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

/* GLOBAL HOVER LOGIC */
div[data-testid="stButton"] button:hover {
    background-color: var(--buddy-green) !important;
    color: white !important;
    border-color: var(--buddy-green) !important;
}

/* ICON BUTTONS (Library Page) */
.icon-btn div[data-testid="stButton"] button {
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    height: 38px !important;
    width: 38px !important;
    padding: 0 !important;
    border: none !important;
    background: transparent !important;
}

/* PINNED BOTTOM-RIGHT DELETE BUTTON */
.card-del-footer {
    display: flex !important;
    justify-content: flex-end !important;
    width: 100% !important;
    margin-top: 1.5rem !important;
}

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

/* PROJECT PAGE STYLES */
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
    if 'renaming_project' not in st.session_state:
        st.session_state.renaming_project = None

    if st.session_state.active_project is None:
        # LIBRARY VIEW (Simplified for this version)
        st.markdown('<div><h1 style="margin:0; font-size: 2.5rem; color:#0000FF;">🗂️ Project Library</h1><p style="color:#18A48C; font-weight: bold; font-size: 1.1rem; margin-bottom: 1.25rem;">Select an existing review or start a new one.</p></div>', unsafe_allow_html=True)
        
        with st.container(border=True):
            c1, c2 = st.columns([4, 1])
            new_name = c1.text_input("New Project Name", placeholder="e.g. AI Ethics 2026", label_visibility="collapsed")
            if c2.button("➕ Create Project", use_container_width=True):
                if new_name and new_name not in st.session_state.projects:
                    st.session_state.projects[new_name] = {"papers": [], "last_accessed": time.time()}
                    save_data(st.session_state.projects)
                    st.session_state.active_project = new_name
                    st.rerun()

        # Render Project List
        projects = list(st.session_state.projects.keys())
        for proj_name in projects:
            with st.container(border=True):
                col_n, col_o = st.columns([8, 1])
                col_n.write(f"📍 **{proj_name}**")
                if col_o.button("➡️", key=f"open_{proj_name}"):
                    st.session_state.active_project = proj_name
                    st.rerun()

    else:
        # PROJECT VIEW
        st.markdown(f'<div class="fixed-header-bg"><div class="fixed-header-text"><h1>{st.session_state.active_project}</h1></div></div>', unsafe_allow_html=True)
        st.markdown('<div class="upload-pull-up">', unsafe_allow_html=True)
        
        llm = None
        if api_key:
            llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", google_api_key=api_key, temperature=0.1)

        uploaded_files = st.file_uploader("Upload academic papers (PDF)", type="pdf", accept_multiple_files=True)
        run_review = st.button("🔬 Analyse paper", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

        current_proj = st.session_state.projects[st.session_state.active_project]
        if isinstance(current_proj, list):
             current_proj = {"papers": current_proj, "last_accessed": time.time()}
             st.session_state.projects[st.session_state.active_project] = current_proj

        if uploaded_files and llm and run_review:
            progress_text = st.empty()
            if 'session_uploads' not in st.session_state: st.session_state.session_uploads = set()
            for file in uploaded_files:
                if file.name in st.session_state.session_uploads: continue
                progress_text.text(f"📖 Critically reviewing: {file.name}...")
                try:
                    reader = PdfReader(file)
                    text = "".join([p.extract_text() for p in reader.pages if p.extract_text()]).strip()
                    prompt = f"PhD systematic review. Labels: [TITLE], [AUTHORS], [YEAR], [REFERENCE], [SUMMARY], [BACKGROUND], [METHODOLOGY], [CONTEXT], [FINDINGS], [RELIABILITY]. Text: {text[:30000]}"
                    res = llm.invoke([HumanMessage(content=prompt)]).content
                    res = re.sub(r'\*', '', res)
                    def ext(label, next_l=None):
                        p = rf"\[{label}\]:?\s*(.*?)(?=\s*\[{next_l}\]|$)" if next_l else rf"\[{label}\]:?\s*(.*)"
                        m = re.search(p, res, re.DOTALL | re.IGNORECASE)
                        return m.group(1).strip() if m else "Not found."
                    
                    # EXTRACT LEAD AUTHOR SURNAME
                    full_authors = ext("AUTHORS", "YEAR")
                    lead_author = full_authors.split(',')[0].split(' ')[0].strip() # Takes first word/name before a comma or space
                    pub_year = ext("YEAR", "REFERENCE")
                    cite_ref = f"{lead_author}, {pub_year}"

                    new_paper = {
                        "Ref": cite_ref,
                        "Title": ext("TITLE", "AUTHORS"), 
                        "Authors": full_authors, 
                        "Year": pub_year, 
                        "Reference": ext("REFERENCE", "SUMMARY"), 
                        "Summary": ext("SUMMARY", "BACKGROUND"), 
                        "Background": ext("BACKGROUND", "METHODOLOGY"), 
                        "Methodology": ext("METHODOLOGY", "CONTEXT"), 
                        "Context": ext("CONTEXT", "FINDINGS"), 
                        "Findings": ext("FINDINGS", "RELIABILITY"), 
                        "Reliability": ext("RELIABILITY")
                    }
                    st.session_state.projects[st.session_state.active_project]["papers"].append(new_paper)
                    st.session_state.session_uploads.add(file.name)
                    save_data(st.session_state.projects)
                except Exception as e: st.error(f"Error: {e}")
            progress_text.empty()
            st.rerun()

        papers_data = st.session_state.projects[st.session_state.active_project]["papers"]
        if papers_data:
            t1, t2, t3 = st.tabs(["🖼️ Individual Papers", "📊 Master Table", "🧠 Synthesis"])
            with t1:
                for idx, r in enumerate(reversed(papers_data)):
                    real_idx = len(papers_data) - 1 - idx
                    with st.container(border=True):
                        col_metric, col_title = st.columns([3, 12])
                        with col_metric: 
                            st.metric("Citation", r['Ref']) # CHANGED FROM # TO REF
                        with col_title: 
                            st.subheader(r['Title'])
                        
                        st.markdown(f'<div><b>Authors:</b> {r["Authors"]}<br><b>Year:</b> {r["Year"]}<br><b>Full Citation:</b> {r["Reference"]}</div>', unsafe_allow_html=True)
                        st.divider()
                        
                        sec = [("📝 Summary", r["Summary"]), ("📖 Background", r["Background"]), ("⚙️ Methodology", r["Methodology"]), ("📍 Context", r["Context"]), ("💡 Findings", r["Findings"]), ("🛡️ Reliability", r["Reliability"])]
                        for k, v in sec: st.markdown(f'<span class="section-title">{k}</span>{v}', unsafe_allow_html=True)
                        
                        st.markdown('<div class="card-del-footer">', unsafe_allow_html=True)
                        if st.button("🗑️ Delete Paper", key=f"del_paper_{real_idx}"):
                            st.session_state.projects[st.session_state.active_project]["papers"].pop(real_idx)
                            save_data(st.session_state.projects)
                            st.rerun()
                        st.markdown('</div>', unsafe_allow_html=True)

            with t2:
                st.dataframe(pd.DataFrame(papers_data), use_container_width=True, hide_index=True)
            
            with t3:
                # Synthesis logic (as per previous working version)
                pass

        st.markdown('<div class="bottom-actions">', unsafe_allow_html=True)
        f1, f2, f3 = st.columns([6, 1, 1])
        with f2:
            if st.button("💾 Save", use_container_width=True):
                save_data(st.session_state.projects)
                st.toast("Saved!")
        with f3:
            if st.button("🏠 Library", use_container_width=True):
                st.session_state.active_project = None
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
