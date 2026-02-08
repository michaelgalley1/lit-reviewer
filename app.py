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
                # Migration logic for file data
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

# 3. STYLING (CSS)
st.markdown("""
<style>
[data-testid="stHeader"] { background-color: rgba(255, 255, 255, 0); }
:root {
    --buddy-green: #18A48C;
    --buddy-blue: #0000FF;
}

/* GLOBAL RESET */
[data-testid="block-container"] {
    padding-top: 1rem !important;
    padding-bottom: 2rem !important;
}

/* -------------------------
   LIBRARY PAGE STYLES
   ------------------------- */
.icon-btn button {
    background: transparent !important;
    border: none !important;
    padding: 0px !important;
    font-size: 1.5rem !important;
    line-height: 1 !important;
    display: flex;
    align-items: center;
    justify-content: center;
    height: 100% !important;
}
.icon-btn button:hover {
    background: #f0f2f6 !important;
    border-radius: 5px !important;
}
.bin-btn button:hover { color: red !important; background: #ffe6e6 !important; }
.arrow-btn button:hover { color: var(--buddy-green) !important; background: #e6fffa !important; }

/* -------------------------
   PROJECT PAGE STYLES
   ------------------------- */

/* FIXED HEADER (Title Only) */
.fixed-header-bg {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 80px; 
    background: white;
    border-bottom: 2px solid #f0f2f6;
    z-index: 1000;
    padding-left: 60px; /* Match Streamlit margin */
    display: flex;
    align-items: center;
}

/* Main Project Title */
.fixed-header-text h1 { 
    margin: 0; 
    font-size: 2.2rem; 
    color: #0000FF; 
    line-height: 1.1; 
}

/* Spacer to push content below fixed header */
.header-spacer {
    height: 80px; 
    width: 100%;
}

/* BOTTOM ACTION BAR - Tightened Spacing */
.bottom-actions {
    margin-top: 10px;      
    padding-top: 10px;     
    padding-bottom: 20px;
    border-top: 1px solid #eee;
}

/* General Input Styling */
[data-testid="stTextInput"] div[data-baseweb="input"] { border: 1px solid #d3d3d3 !important; }
[data-testid="stTextInput"] div[data-baseweb="input"]:focus-within { border: 2px solid var(--buddy-green) !important; }

/* Button General */
div.stButton > button:first-child {
    border: 1px solid var(--buddy-green) !important;
    color: var(--buddy-green) !important;
    background: transparent !important;
    font-weight: bold !important;
}
div.stButton > button:hover {
    background: var(--buddy-green) !important;
    color: white !important;
}

.section-title { font-weight: bold; color: #0000FF; margin-top: 15px; display: block; text-transform: uppercase; font-size: 0.85rem; border-bottom: 1px solid #eee; }
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

    # ==========================================
    # VIEW 1: HOME PAGE (Project Library)
    # ==========================================
    if st.session_state.active_project is None:
        
        st.markdown("""
        <div>
            <h1 style="margin:0; font-size: 2.5rem; color:#0000FF;">🗂️ Project Library</h1>
            <p style="color:#18A48C; font-weight: bold; font-size: 1.1rem; margin-bottom: 20px;">Select an existing review or start a new one.</p>
        </div>
        """, unsafe_allow_html=True)

        with st.container(border=True):
            c1, c2 = st.columns([4, 1])
            new_name = c1.text_input("New Project Name", placeholder="e.g. AI Ethics 2026", label_visibility="collapsed")
            if c2.button("➕ Create Project", use_container_width=True):
                if new_name and new_name not in st.session_state.projects:
                    # Create with timestamp
                    st.session_state.projects[new_name] = {"papers": [], "last_accessed": time.time()}
                    save_data(st.session_state.projects)
                    st.session_state.active_project = new_name
                    st.rerun()
                elif new_name in st.session_state.projects:
                    st.error("Project already exists.")

        # NO SPACER HERE - TIGHT LAYOUT
        
        projects = list(st.session_state.projects.keys())
        
        if not projects:
            st.info("No projects yet.")
        else:
            # SAFETY SORT: Handles both old list format and new dict format
            def get_timestamp(proj_key):
                data = st.session_state.projects[proj_key]
                if isinstance(data, dict):
                    return data.get("last_accessed", 0)
                return 0 # Old format gets 0 timestamp (bottom of list)

            sorted_projects = sorted(projects, key=get_timestamp, reverse=True)

            st.markdown("### Your Projects")
            for proj_name in sorted_projects:
                with st.container(border=True):
                    col_name, col_spacer, col_del, col_open = st.columns([6, 2, 0.5, 0.5])
                    
                    with col_name:
                        # Handle both old list format and new dict format safely
                        proj_data = st.session_state.projects[proj_name]
                        if isinstance(proj_data, list):
                            paper_count = len(proj_data)
                        else:
                            paper_count = len(proj_data.get("papers", []))
                            
                        st.markdown(f"<div style='display:flex; flex-direction:column; justify-content:center; height:100%;'>"
                                    f"<h3 style='margin:0; padding:0; font-size:1.1rem; color:#333;'>📍 {proj_name}</h3>"
                                    f"<span style='font-size:0.85rem; color:#666;'>📚 {paper_count} Papers</span></div>", unsafe_allow_html=True)
                    
                    with col_del:
                        st.markdown('<div class="icon-btn bin-btn">', unsafe_allow_html=True)
                        if st.button("🗑️", key=f"del_{proj_name}", help=f"Delete {proj_name}"):
                            del st.session_state.projects[proj_name]
                            save_data(st.session_state.projects)
                            st.rerun()
                        st.markdown('</div>', unsafe_allow_html=True)
                    
                    with col_open:
                        st.markdown('<div class="icon-btn arrow-btn">', unsafe_allow_html=True)
                        if st.button("➡️", key=f"open_{proj_name}", help=f"Open {proj_name}"):
                            st.session_state.active_project = proj_name
                            
                            # Upgrade old data format on fly if needed
                            if isinstance(st.session_state.projects[proj_name], list):
                                st.session_state.projects[proj_name] = {"papers": st.session_state.projects[proj_name], "last_accessed": time.time()}
                            else:
                                st.session_state.projects[proj_name]["last_accessed"] = time.time()
                            
                            save_data(st.session_state.projects)
                            st.rerun()
                        st.markdown('</div>', unsafe_allow_html=True)

    # ==========================================
    # VIEW 2: ANALYSIS DASHBOARD (Individual Project)
    # ==========================================
    else:
        # 1. FIXED HEADER
        st.markdown(f'''
        <div class="fixed-header-bg">
            <div class="fixed-header-text">
                <h1>{st.session_state.active_project}</h1>
            </div>
        </div>
        <div class="header-spacer"></div>
        ''', unsafe_allow_html=True)

        # 2. MAIN CONTENT
        llm = None
        if api_key:
            llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", google_api_key=api_key, temperature=0.1)

        uploaded_files = st.file_uploader("Upload academic papers (PDF)", type="pdf", accept_multiple_files=True)
        run_review = st.button("🔬 Analyse paper", use_container_width=True)

        # Ensure current project data is in correct format (dict)
        current_proj = st.session_state.projects[st.session_state.active_project]
        if isinstance(current_proj, list):
             current_proj = {"papers": current_proj, "last_accessed": time.time()}
             st.session_state.projects[st.session_state.active_project] = current_proj

        if uploaded_files and llm and run_review:
            progress_text = st.empty()
            if 'session_uploads' not in st.session_state: st.session_state.session_uploads = set()

            for i, file in enumerate(uploaded_files):
                if file.name in st.session_state.session_uploads: continue
                
                progress_text.text(f"📖 Critically reviewing: {file.name}...")
                try:
                    reader = PdfReader(file)
                    text = "".join([p.extract_text() for p in reader.pages if p.extract_text()]).strip()
                    prompt = f"""
                    You are a PhD Candidate performing a Systematic Literature Review. Analyze the provided text with extreme academic rigour.
                    Avoid excessive use of commas; provide fluid, sophisticated academic prose.
                    Structure your response using ONLY these labels:
                    [TITLE], [AUTHORS], [YEAR], [REFERENCE], [SUMMARY], [BACKGROUND], [METHODOLOGY], [CONTEXT], [FINDINGS], [RELIABILITY].

                    Requirements:
                    - [METHODOLOGY]: Design critique, sampling, and statistical validity.
                    - [RELIABILITY]: Discuss internal/external validity and potential biases.
                    - No bolding (**). No lists. Use sophisticated academic prose.

                    FULL TEXT: {text[:30000]}
                    """
                    res = llm.invoke([HumanMessage(content=prompt)]).content
                    res = re.sub(r'\*', '', res)

                    def ext(label, next_l=None):
                        p = rf"\[{label}\]:?\s*(.*?)(?=\s*\[{next_l}\]|$)" if next_l else rf"\[{label}\]:?\s*(.*)"
                        m = re.search(p, res, re.DOTALL | re.IGNORECASE)
                        return m.group(1).strip() if m else "Not found."

                    new_paper = {
                        "#": len(current_proj["papers"]) + 1,
                        "Title": ext("TITLE", "AUTHORS"),
                        "Authors": ext("AUTHORS", "YEAR"),
                        "Year": ext("YEAR", "REFERENCE"),
                        "Reference": ext("REFERENCE", "SUMMARY"),
                        "Summary": ext("SUMMARY", "BACKGROUND"),
                        "Background": ext("BACKGROUND", "METHODOLOGY"),
                        "Methodology": ext("METHODOLOGY", "CONTEXT"),
                        "Context": ext("CONTEXT", "FINDINGS"),
                        "Findings": ext("FINDINGS", "RELIABILITY"),
                        "Reliability": ext("RELIABILITY")
                    }
                    
                    st.session_state.projects[st.session_state.active_project]["papers"].append(new_paper)
                    st.session_state.projects[st.session_state.active_project]["last_accessed"] = time.time()
                    
                    st.session_state.session_uploads.add(file.name)
                    save_data(st.session_state.projects)
                    
                except Exception as e: st.error(f"Error on {file.name}: {e}")
            progress_text.empty()
            st.rerun()

        papers_data = st.session_state.projects[st.session_state.active_project]["papers"]

        if papers_data:
            t1, t2, t3 = st.tabs(["🖼️ Card Gallery", "📊 Master Table", "🧠 Synthesis"])
            with t1:
                for r in reversed(papers_data):
                    with st.container(border=True):
                        cr, ct = st.columns([1, 12]); cr.metric("Ref", r['#']); ct.subheader(r['Title'])
                        st.markdown(f'''
                            <div class="metadata-block">
                                <span class="metadata-item">🖊️ <b>Authors:</b> {r["Authors"]}</span>
                                <span class="metadata-item">🗓️ <b>Year:</b> {r["Year"]}</span>
                                <span class="metadata-item">🔗 <b>Full Citation:</b> {r["Reference"]}</span>
                            </div>
                        ''', unsafe_allow_html=True)
                        st.divider()
                        sec = [("📝 Summary", r["Summary"]), ("📖 Background", r["Background"]), ("⚙️ Methodology", r["Methodology"]), ("📍 Context", r["Context"]), ("💡 Findings", r["Findings"]), ("🛡️ Reliability", r["Reliability"])]
                        for k, v in sec:
                            st.markdown(f'<span class="section-title">{k}</span><span class="section-content">{v}</span>', unsafe_allow_html=True)
            with t2:
                df = pd.DataFrame(papers_data)
                st.dataframe(df, use_container_width=True, hide_index=True)
                csv = df.to_csv(index=False).encode('utf-8-sig')
                st.download_button(
                    label="📊 Export as CSV file",
                    data=csv,
                    file_name=f"{st.session_state.active_project}_review.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            with t3:
                if len(papers_data) > 0:
                    with st.spinner("Performing meta-synthesis..."):
                        evidence_base = ""
                        for r in papers_data:
                            evidence_base += f"Paper {r['#']} ({r['Year']}): Findings: {r['Findings']}. Methodology: {r['Methodology']}\n\n"

                        synth_prompt = f"Meta-Synthesis: Analyze theoretical contributions and trends. Use [OVERVIEW], [PATTERNS], [CONTRADICTIONS], [FUTURE_DIRECTIONS]. Academic prose, no bolding.\n\nEvidence Base:\n{evidence_base}"
                        raw_synth = llm.invoke([HumanMessage(content=synth_prompt)]).content
                        clean_synth = re.sub(r'\*', '', raw_synth)

                        def get_synth(label, next_l=None):
                            p = rf"\[{label}\]:?\s*(.*?)(?=\s*\[{next_l}\]|$)" if next_l else rf"\[{label}\]:?\s*(.*)"
                            m = re.search(p, clean_synth, re.DOTALL | re.IGNORECASE)
                            return m.group(1).strip() if m else "Detail not found."

                        with st.container(border=True):
                            st.markdown("### 🎯 Executive Overview"); st.write(get_synth("OVERVIEW", "PATTERNS"))
                        with st.container(border=True):
                            st.markdown("### 📈 Cross-Study Patterns"); st.write(get_synth("PATTERNS", "CONTRADICTIONS"))
                        with st.container(border=True):
                            st.markdown("### ⚖️ Conflicts & Contradictions"); st.write(get_synth("CONTRADICTIONS", "FUTURE_DIRECTIONS"))
                        with st.container(border=True):
                            st.markdown("### 🚀 Future Research Directions"); st.write(get_synth("FUTURE_DIRECTIONS"))

        # 3. BOTTOM BUTTONS (Footer Area)
        st.markdown('<div class="bottom-actions">', unsafe_allow_html=True)
        
        f1, f2, f3 = st.columns([6, 1, 1])
        with f2:
            if st.button("💾 Save Progress", use_container_width=True):
                save_data(st.session_state.projects)
                st.toast("Saved!", icon="✅")
        with f3:
            if st.button("🏠 Library", use_container_width=True):
                save_data(st.session_state.projects)
                st.session_state.active_project = None
                st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)
