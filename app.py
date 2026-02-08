import streamlit as st
import pandas as pd
from pypdf import PdfReader
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
from streamlit_gsheets import GSheetsConnection
import re
import json
import os
import time

# 1. PAGE CONFIGURATION
st.set_page_config(page_title="Literature Review Buddy", page_icon="📚", layout="wide")

# 2. DATABASE CONNECTION (Google Sheets)
conn = st.connection("gsheets", type=GSheetsConnection)

def load_full_library():
    try:
        df = conn.read(ttl=0)
        if df is None or df.empty: return {}
        
        library = {}
        for _, row in df.iterrows():
            proj = row.get('Project')
            if not proj: continue
            if proj not in library:
                library[proj] = {"papers": [], "last_accessed": row.get('LastAccessed', 0)}
            
            if pd.notna(row.get('Title')):
                library[proj]["papers"].append({
                    "#": row.get('#'), "Title": row.get('Title'), "Authors": row.get('Authors'),
                    "Year": row.get('Year'), "Reference": row.get('Reference'), "Summary": row.get('Summary'),
                    "Background": row.get('Background'), "Methodology": row.get('Methodology'),
                    "Context": row.get('Context'), "Findings": row.get('Findings'), "Reliability": row.get('Reliability')
                })
        return library
    except Exception as e:
        return {}

def save_full_library(library):
    flat_data = []
    for proj_name, content in library.items():
        if not content["papers"]:
            flat_data.append({"Project": proj_name, "LastAccessed": content["last_accessed"]})
        else:
            for paper in content["papers"]:
                row = {"Project": proj_name, "LastAccessed": content["last_accessed"]}
                row.update(paper)
                flat_data.append(row)
    
    if flat_data:
        new_df = pd.DataFrame(flat_data)
        conn.update(data=new_df)

# 3. STYLING
st.markdown("""
<style>
[data-testid="stHeader"] { background-color: rgba(255, 255, 255, 0); }
:root { --buddy-green: #18A48C; --buddy-blue: #0000FF; }
[data-testid="stTextInput"] div[data-baseweb="input"] { border: 1px solid #d3d3d3 !important; }
[data-testid="stTextInput"] div[data-baseweb="input"]:hover { border-color: var(--buddy-green) !important; }
[data-testid="stTextInput"] div[data-baseweb="input"]:focus-within { border: 2px solid var(--buddy-green) !important; }
div[data-testid="stButton"] button:hover { background-color: var(--buddy-green) !important; color: white !important; }
.section-title { font-weight: bold; color: #0000FF; margin-top: 1rem; display: block; text-transform: uppercase; font-size: 0.85rem; border-bottom: 0.06rem solid #eee; }
.section-content { display: block; margin-bottom: 10px; line-height: 1.6; color: #333; }
.fixed-header-bg { position: fixed; top: 0; left: 0; width: 100%; height: 4.5rem; background: white; border-bottom: 0.125rem solid #f0f2f6; z-index: 1000; padding-left: 3.75rem; display: flex; align-items: center; }
.fixed-header-text h1 { margin: 0; font-size: 2.2rem; color: #0000FF; }
.upload-pull-up { margin-top: -3.0rem !important; }
.card-del-container { display: flex; justify-content: flex-end; width: 100%; margin-top: 1.5rem; }
.card-del-container div[data-testid="stButton"] button { color: #ff4b4b !important; border: 1px solid #ff4b4b !important; background: transparent !important; font-size: 0.85rem !important; min-width: 140px !important; }
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
            else: st.error("🚫 Access Denied")
        return False
    return True

# 5. MAIN LOGIC
if check_password():
    api_key = st.secrets.get("GEMINI_API_KEY")

    if 'projects' not in st.session_state:
        st.session_state.projects = load_full_library()
    
    if 'active_project' not in st.session_state:
        st.session_state.active_project = None 

    if st.session_state.active_project is None:
        # --- LIBRARY VIEW ---
        st.markdown('<div><h1 style="color:#0000FF;">🗂️ Project Library</h1><p style="color:#18A48C; font-weight: bold;">Permanent Cloud Storage Active.</p></div>', unsafe_allow_html=True)

        with st.container(border=True):
            c1, c2 = st.columns([4, 1])
            new_name = c1.text_input("New Project Name", placeholder="e.g. AI Ethics", label_visibility="collapsed")
            if c2.button("➕ Create Project", use_container_width=True):
                if new_name and new_name not in st.session_state.projects:
                    st.session_state.projects[new_name] = {"papers": [], "last_accessed": time.time()}
                    save_full_library(st.session_state.projects)
                    st.session_state.active_project = new_name
                    st.rerun()

        projects = list(st.session_state.projects.keys())
        if projects:
            sorted_projects = sorted(projects, key=lambda k: st.session_state.projects[k].get("last_accessed", 0), reverse=True)
            for proj_name in sorted_projects:
                with st.container(border=True):
                    col_name, col_spacer, col_edit, col_del, col_open = st.columns([6, 1.5, 0.5, 0.5, 0.5])
                    with col_name:
                        p_count = len(st.session_state.projects[proj_name]["papers"])
                        st.markdown(f"**📍 {proj_name}** ({p_count} Papers)")
                    with col_del:
                        if st.button("🗑️", key=f"del_{proj_name}"):
                            del st.session_state.projects[proj_name]
                            save_full_library(st.session_state.projects)
                            st.rerun()
                    with col_open:
                        if st.button("➡️", key=f"open_{proj_name}"):
                            st.session_state.active_project = proj_name
                            st.session_state.projects[proj_name]["last_accessed"] = time.time()
                            save_full_library(st.session_state.projects)
                            st.rerun()

    else:
        # --- PROJECT VIEW ---
        st.markdown(f'<div class="fixed-header-bg"><div class="fixed-header-text"><h1>{st.session_state.active_project}</h1></div></div>', unsafe_allow_html=True)
        st.markdown('<div class="upload-pull-up">', unsafe_allow_html=True)
        
        llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", google_api_key=api_key, temperature=0.1) if api_key else None
        uploaded_files = st.file_uploader("Upload academic papers (PDF)", type="pdf", accept_multiple_files=True)
        run_review = st.button("🔬 Analyse paper", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

        current_proj = st.session_state.projects[st.session_state.active_project]

        if uploaded_files and llm and run_review:
            progress_text = st.empty()
            if 'session_uploads' not in st.session_state: st.session_state.session_uploads = set()
            for file in uploaded_files:
                if file.name in st.session_state.session_uploads: continue
                progress_text.text(f"📖 Critically reviewing: {file.name}...")
                try:
                    reader = PdfReader(file)
                    text = "".join([p.extract_text() for p in reader.pages if p.extract_text()]).strip()
                    
                    prompt = (
                        "Act as a Senior Academic Researcher and PhD Supervisor specializing in Systematic Literature Reviews. "
                        "Evaluate the logic, methodology, and contribution to the field. "
                        "Carefully analyze the text and extract for the following categories:\n\n"
                        "[TITLE]: The full title.\n[AUTHORS]: All primary authors.\n[YEAR]: Year of publication.\n"
                        "[REFERENCE]: Full Harvard-style citation.\n"
                        "[SUMMARY]: 2-3 sentence overview of objective and outcome.\n"
                        "[BACKGROUND]: Specific gap and theoretical framework.\n"
                        "[METHODOLOGY]: Design, sample size (N=), and instruments.\n"
                        "[CONTEXT]: Geography and population included.\n"
                        "[FINDINGS]: Results, statistical significance, and relation to seminal works.\n"
                        "[RELIABILITY]: Critique limitations, biases, and check p-values/CIs.\n\n"
                        "STRICT RULES: Output ONLY bracketed labels. No bolding or bullets. TEXT: " + text[:30000]
                    )
                    
                    res = llm.invoke([HumanMessage(content=prompt)]).content
                    res = re.sub(r'\*', '', res) 
                    
                    def ext(label):
                        p = rf"\[{label}\]\s*:?\s*(.*?)(?=\s*\[|$)"
                        m = re.search(p, res, re.DOTALL | re.IGNORECASE)
                        return m.group(1).strip() if m else "Not explicitly stated."
                    
                    new_paper = {
                        "#": len(current_proj["papers"]) + 1, 
                        "Title": ext("TITLE"), "Authors": ext("AUTHORS"), "Year": ext("YEAR"), 
                        "Reference": ext("REFERENCE"), "Summary": ext("SUMMARY"), 
                        "Background": ext("BACKGROUND"), "Methodology": ext("METHODOLOGY"), 
                        "Context": ext("CONTEXT"), "Findings": ext("FINDINGS"), 
                        "Reliability": ext("RELIABILITY")
                    }
                    st.session_state.projects[st.session_state.active_project]["papers"].append(new_paper)
                    st.session_state.projects[st.session_state.active_project]["last_accessed"] = time.time()
                    st.session_state.session_uploads.add(file.name)
                    save_full_library(st.session_state.projects)
                except Exception as e: st.error(f"Error: {e}")
            progress_text.empty()
            st.rerun()

        papers_data = st.session_state.projects[st.session_state.active_project]["papers"]
        if papers_data:
            t1, t2 = st.tabs(["🖼️ Individual Papers", "📊 Master Table"])
            with t1:
                for idx, r in enumerate(reversed(papers_data)):
                    real_idx = len(papers_data) - 1 - idx
                    with st.container(border=True):
                        st.subheader(f"Ref {r.get('#')}: {r.get('Title')}")
                        st.markdown(f'🖊️ Authors: {r.get("Authors")} | 🗓️ Year: {r.get("Year")}')
                        st.divider()
                        sections = [("📝 Summary", r.get("Summary")), ("📖 Background", r.get("Background")), ("⚙️ Methodology", r.get("Methodology")), ("📍 Context", r.get("Context")), ("💡 Findings", r.get("Findings")), ("🛡️ Reliability", r.get("Reliability"))]
                        for k, v in sections: 
                            st.markdown(f'<span class="section-title">{k}</span><span class="section-content">{v}</span>', unsafe_allow_html=True)
                        
                        st.markdown('<div class="card-del-container">', unsafe_allow_html=True)
                        if st.button("🗑️ Delete Paper", key=f"del_paper_{real_idx}"):
                            st.session_state.projects[st.session_state.active_project]["papers"].pop(real_idx)
                            for i, p in enumerate(st.session_state.projects[st.session_state.active_project]["papers"]): p["#"] = i + 1
                            save_full_library(st.session_state.projects)
                            st.rerun()
                        st.markdown('</div>', unsafe_allow_html=True)
            with t2:
                df = pd.DataFrame(papers_data)
                st.dataframe(df, use_container_width=True, hide_index=True)

        st.markdown('<div class="bottom-actions">', unsafe_allow_html=True)
        f1, f2 = st.columns([8, 1])
        with f2:
            if st.button("🏠 Library", key="final_lib", use_container_width=True):
                st.session_state.active_project = None; st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
