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
   ICON BUTTONS (Library Page)
   ------------------------- */
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

/* -------------------------
   CARD DELETE BUTTON (Expansion & Alignment Fix)
   ------------------------- */
.card-del-container {
    display: flex;
    justify-content: flex-end;
    width: 100%;
}

.card-del-container div[data-testid="stButton"] button {
    color: #ff4b4b !important;
    border: 1px solid #ff4b4b !important;
    background: transparent !important;
    font-size: 0.85rem !important;
    height: 34px !important;
    padding: 0 15px !important;
    
    /* FORCE SINGLE LINE & WIDTH */
    white-space: nowrap !important;
    min-width: 140px !important; 
    width: auto !important;
    display: block !important;
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

[data-testid="stTextInput"] div[data-baseweb="input"] { border: 0.06rem solid #d3d3d3 !important; }
[data-testid="stTextInput"] div[data-baseweb="input"]:focus-within { border: 0.125rem solid var(--buddy-green) !important; }

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
        # LIBRARY VIEW
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
                elif new_name in st.session_state.projects:
                    st.error("Project already exists.")

        projects = list(st.session_state.projects.keys())
        if projects:
            def get_timestamp(proj_key):
                data = st.session_state.projects[proj_key]
                return data.get("last_accessed", 0) if isinstance(data, dict) else 0
            sorted_projects = sorted(projects, key=get_timestamp, reverse=True)
            st.markdown("### Your Projects")
            for proj_name in sorted_projects:
                with st.container(border=True):
                    if st.session_state.renaming_project == proj_name:
                        r_col1, r_col2, r_col3 = st.columns([6, 1, 1])
                        with r_col1: new_name_val = st.text_input("Rename", value=proj_name, label_visibility="collapsed", key=f"input_{proj_name}")
                        with r_col2: 
                            if st.button("✅", key=f"save_rename_{proj_name}", use_container_width=True):
                                st.session_state.projects[new_name_val] = st.session_state.projects.pop(proj_name)
                                save_data(st.session_state.projects)
                                st.session_state.renaming_project = None
                                st.rerun()
                        with r_col3:
                            if st.button("❌", key=f"cancel_rename_{proj_name}", use_container_width=True):
                                st.session_state.renaming_project = None
                                st.rerun()
                    else:
                        col_name, col_spacer, col_edit, col_del, col_open = st.columns([6, 1.5, 0.5, 0.5, 0.5])
                        with col_name:
                            proj_data = st.session_state.projects[proj_name]
                            p_count = len(proj_data["papers"]) if isinstance(proj_data, dict) else len(proj_data)
                            st.markdown(f"<div style='display:flex; flex-direction:column; justify-content:center; height:100%;'><h3 style='margin:0; padding:0; font-size:1.1rem; color:#333;'>📍 {proj_name}</h3><span style='font-size:0.85rem; color:#666;'>📚 {p_count} Papers</span></div>", unsafe_allow_html=True)
                        with col_edit:
                            st.markdown('<div class="icon-btn edit-btn">', unsafe_allow_html=True)
                            if st.button("🖊️", key=f"edit_{proj_name}"):
                                st.session_state.renaming_project = proj_name
                                st.rerun()
                            st.markdown('</div>', unsafe_allow_html=True)
                        with col_del:
                            st.markdown('<div class="icon-btn bin-btn">', unsafe_allow_html=True)
                            if st.button("🗑️", key=f"del_{proj_name}"):
                                del st.session_state.projects[proj_name]
                                save_data(st.session_state.projects)
                                st.rerun()
                            st.markdown('</div>', unsafe_allow_html=True)
                        with col_open:
                            st.markdown('<div class="icon-btn arrow-btn">', unsafe_allow_html=True)
                            if st.button("➡️", key=f"open_{proj_name}"):
                                st.session_state.active_project = proj_name
                                if isinstance(st.session_state.projects[proj_name], list):
                                    st.session_state.projects[proj_name] = {"papers": st.session_state.projects[proj_name], "last_accessed": time.time()}
                                else:
                                    st.session_state.projects[proj_name]["last_accessed"] = time.time()
                                save_data(st.session_state.projects)
                                st.rerun()
                            st.markdown('</div>', unsafe_allow_html=True)

    else:
        st.markdown(f'<div class="fixed-header-bg"><div class="fixed-header-text"><h1>{st.session_state.active_project}</h1></div></div>', unsafe_allow_html=True)
        st.markdown('<div class="upload-pull-up">', unsafe_allow_html=True)
        llm = None
        if api_key: llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", google_api_key=api_key, temperature=0.1)
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
                    new_paper = {"#": len(current_proj["papers"]) + 1, "Title": ext("TITLE", "AUTHORS"), "Authors": ext("AUTHORS", "YEAR"), "Year": ext("YEAR", "REFERENCE"), "Reference": ext("REFERENCE", "SUMMARY"), "Summary": ext("SUMMARY", "BACKGROUND"), "Background": ext("BACKGROUND", "METHODOLOGY"), "Methodology": ext("METHODOLOGY", "CONTEXT"), "Context": ext("CONTEXT", "FINDINGS"), "Findings": ext("FINDINGS", "RELIABILITY"), "Reliability": ext("RELIABILITY")}
                    st.session_state.projects[st.session_state.active_project]["papers"].append(new_paper)
                    st.session_state.projects[st.session_state.active_project]["last_accessed"] = time.time()
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
                        # Increased column for delete to 2.5
                        col_metric, col_title, col_del = st.columns([1, 10, 2.5])
                        with col_metric: st.metric("Ref", r['#'])
                        with col_title: st.subheader(r['Title'])
                        with col_del:
                            st.markdown('<div class="card-del-container">', unsafe_allow_html=True)
                            if st.button("🗑️ Delete Paper", key=f"del_paper_{real_idx}"):
                                st.session_state.projects[st.session_state.active_project]["papers"].pop(real_idx)
                                for i, p in enumerate(st.session_state.projects[st.session_state.active_project]["papers"]): p["#"] = i + 1
                                save_data(st.session_state.projects)
                                st.rerun()
                            st.markdown('</div>', unsafe_allow_html=True)
                        st.markdown(f'<div class="metadata-block"><span class="metadata-item">🖊️ Authors: {r["Authors"]}</span><br><span class="metadata-item">🗓️ Year: {r["Year"]}</span><br><span class="metadata-item">🔗 Full Citation: {r["Reference"]}</span></div>', unsafe_allow_html=True)
                        st.divider()
                        sec = [("📝 Summary", r["Summary"]), ("📖 Background", r["Background"]), ("⚙️ Methodology", r["Methodology"]), ("📍 Context", r["Context"]), ("💡 Findings", r["Findings"]), ("🛡️ Reliability", r["Reliability"])]
                        for k, v in sec: st.markdown(f'<span class="section-title">{k}</span><span class="section-content">{v}</span>', unsafe_allow_html=True)
            with t2:
                df = pd.DataFrame(papers_data)
                st.dataframe(df, use_container_width=True, hide_index=True)
                csv = df.to_csv(index=False).encode('utf-8-sig')
                st.download_button(label="📊 Export CSV", data=csv, file_name=f"{st.session_state.active_project}.csv", use_container_width=True)
            with t3:
                with st.spinner("Meta-Synthesis..."):
                    evidence = ""
                    for r in papers_data: evidence += f"Paper {r['#']} ({r['Year']}): Findings: {r['Findings']}. Methodology: {r['Methodology']}\n\n"
                    synth_p = f"Synthesis of literature. Labels: [OVERVIEW], [PATTERNS], [CONTRADICTIONS], [FUTURE]. Evidence: {evidence}"
                    raw_s = llm.invoke([HumanMessage(content=synth_p)]).content
                    clean_s = re.sub(r'\*', '', raw_s)
                    def gs(l, n=None):
                        p = rf"\[{l}\]:?\s*(.*?)(?=\s*\[{n}\]|$)" if n else rf"\[{l}\]:?\s*(.*)"
                        m = re.search(p, clean_s, re.DOTALL | re.IGNORECASE); return m.group(1).strip() if m else "Detail not found."
                    st.markdown("### 🎯 Executive Overview"); st.write(gs("OVERVIEW", "PATTERNS"))
                    st.markdown("### 📈 Cross-Study Patterns"); st.write(gs("PATTERNS", "CONTRADICTIONS"))
                    st.markdown("### ⚖️ Conflicts & Contradictions"); st.write(gs("CONTRADICTIONS", "FUTURE"))
                    st.markdown("### 🚀 Future Research Directions"); st.write(gs("FUTURE"))

        st.markdown('<div class="bottom-actions">', unsafe_allow_html=True)
        f1, f2, f3 = st.columns([6, 1, 1])
        with f2:
            if st.button("💾 Save", key="final_save", use_container_width=True):
                save_data(st.session_state.projects); st.toast("Saved!", icon="✅")
        with f3:
            if st.button("🏠 Library", key="final_lib", use_container_width=True):
                save_data(st.session_state.projects); st.session_state.active_project = None; st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
