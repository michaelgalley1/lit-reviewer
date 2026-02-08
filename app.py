import streamlit as st
import pandas as pd
from pypdf import PdfReader
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
import re
import time
import json
import os

# 1. PAGE CONFIGURATION
st.set_page_config(page_title="Literature Review Buddy", page_icon="📚", layout="wide")

# 2. STORAGE LOGIC (New)
DB_FILE = "buddy_library.json"

def load_data():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f:
                data = json.load(f)
                return data if data else {"Default Project": []}
        except:
            return {"Default Project": []}
    return {"Default Project": []}

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

    /* Input box styling */
    [data-testid="stTextInput"] div[data-baseweb="input"] {
        border: 1px solid #d3d3d3 !important;
    }
    
    [data-testid="stTextInput"] div[data-baseweb="input"]:focus-within {
        border: 2px solid var(--buddy-green) !important;
        box-shadow: none !important;
    }
    
    input:focus {
        outline: none !important;
        box-shadow: none !important;
    }

    .sticky-wrapper {
        position: fixed; top: 0; left: 0; width: 100%;
        background-color: white; z-index: 1000;
        padding: 10px 50px 0px 50px;
        border-bottom: 2px solid #f0f2f6;
    }
    
    .main-content { margin-top: -75px; }
    .block-container { padding-top: 0rem !important; }

    /* UNIFIED BUTTON STYLING */
    div.stButton > button:first-child, div.stDownloadButton > button:first-child {
        width: 100% !important; 
        color: var(--buddy-green) !important;
        border: 2px solid var(--buddy-green) !important; 
        font-weight: bold !important;
        background-color: transparent !important;
        padding-top: 10px !important;
        padding-bottom: 10px !important;
    }
    
    div.stButton > button:hover, div.stDownloadButton > button:hover {
        background-color: var(--buddy-green) !important;
        color: white !important;
    }

    /* Sidebar Delete Button Styling */
    .del-btn > div > button {
        border: none !important;
        color: #ff4b4b !important;
        background: transparent !important;
        padding: 0px !important; 
        height: auto !important;
    }
    .del-btn > div > button:hover {
        color: white !important;
        background: #ff4b4b !important;
    }

    .section-title { font-weight: bold; color: #0000FF; margin-top: 15px; display: block; text-transform: uppercase; font-size: 0.85rem; border-bottom: 1px solid #eee; }
    .section-content { display: block; margin-bottom: 10px; line-height: 1.6; color: #333; }
    
    .metadata-block { margin-bottom: 10px; }
    .metadata-item { color: #444; font-size: 0.95rem; margin-bottom: 4px; display: block; }
    </style>
    """, unsafe_allow_html=True)

# 4. AUTHENTICATION
def check_password():
    correct_password = st.secrets.get("APP_PASSWORD")
    if "password_correct" not in st.session_state:
        st.markdown('<h1 style="margin:0; font-size: 1.8rem; color:#0000FF;">📚 Literature Review Buddy</h1>', unsafe_allow_html=True)
        st.markdown('<p style="color:#18A48C; font-weight: bold; margin-bottom:20px;">Your PhD-Level Research Assistant</p>', unsafe_allow_html=True)
        pwd = st.text_input("Enter password to unlock Literature Review Buddy", type="password")
        if st.button("Unlock Tool"):
            if pwd == correct_password:
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("🚫 Access Denied")
        return False
    return True

# 5. MAIN APPLICATION
if check_password():
    api_key = st.secrets.get("GEMINI_API_KEY")

    # --- NEW: LOAD PROJECTS FROM FILE ---
    if 'projects' not in st.session_state:
        st.session_state.projects = load_data()
    
    if 'active_project' not in st.session_state:
        # Default to the first available project
        if st.session_state.projects:
            st.session_state.active_project = list(st.session_state.projects.keys())[0]
        else:
            st.session_state.projects = {"Default Project": []}
            st.session_state.active_project = "Default Project"
            save_data(st.session_state.projects)

    if 'processed_filenames' not in st.session_state: st.session_state.processed_filenames = set() 

    # --- SIDEBAR: PROJECT MANAGEMENT ---
    with st.sidebar:
        st.title("📁 Research Manager")
        
        # Create New Project
        new_proj_name = st.text_input("New Project Name", placeholder="e.g. AI Ethics 2026")
        if st.button("➕ Create Project"):
            if new_proj_name and new_proj_name not in st.session_state.projects:
                st.session_state.projects[new_proj_name] = []
                st.session_state.active_project = new_proj_name
                save_data(st.session_state.projects)
                st.rerun()
        
        st.divider()
        st.subheader("Your Projects")
        
        # Project Button List
        for proj in list(st.session_state.projects.keys()):
            cols = st.columns([5, 1])
            is_active = (proj == st.session_state.active_project)
            label = f"📍 {proj}" if is_active else proj
            
            # Switch Project
            if cols[0].button(label, key=f"sel_{proj}", use_container_width=True, type="primary" if is_active else "secondary"):
                st.session_state.active_project = proj
                st.rerun()
            
            # Delete Project
            if len(st.session_state.projects) > 1:
                with cols[1]:
                    st.markdown('<div class="del-btn">', unsafe_allow_html=True)
                    if st.button("×", key=f"del_{proj}", help=f"Delete {proj}"):
                        del st.session_state.projects[proj]
                        if is_active:
                            st.session_state.active_project = list(st.session_state.projects.keys())[0]
                        save_data(st.session_state.projects)
                        st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)

    # --- MAIN PAGE ---
    st.markdown(f'''
        <div class="sticky-wrapper">
            <h1 style="margin:0; font-size: 1.8rem; color:#0000FF;">📚 Literature Review Buddy</h1>
            <p style="color:#18A48C; margin-bottom:5px; font-weight: bold;">Active Project: {st.session_state.active_project}</p>
        </div>
    ''', unsafe_allow_html=True)

    with st.container():
        st.write("##") 
        st.markdown('<div class="main-content">', unsafe_allow_html=True)
        
        # SAVE BUTTON (Permanently saves to JSON)
        c1, c2 = st.columns([6, 1])
        with c2:
            if st.button("💾 Save Progress"):
                save_data(st.session_state.projects)
                st.toast("Project saved to disk!", icon="✅")

        llm = None
        if api_key:
            llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", google_api_key=api_key, temperature=0.1)

        uploaded_files = st.file_uploader("Upload academic papers (PDF)", type="pdf", accept_multiple_files=True)
        run_review = st.button("🔬 Analyse paper", use_container_width=True)

        # --- ANALYSIS LOGIC ---
        if uploaded_files and llm and run_review:
            progress_text = st.empty()
            # Check duplicates based on titles already in the ACTIVE project
            current_project_data = st.session_state.projects[st.session_state.active_project]
            
            for i, file in enumerate(uploaded_files):
                if file.name in st.session_state.processed_filenames: continue
                
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

                    # Append to the ACTIVE project list
                    st.session_state.projects[st.session_state.active_project].append({
                        "#": len(st.session_state.projects[st.session_state.active_project]) + 1,
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
                    })
                    st.session_state.processed_filenames.add(file.name)
                except Exception as e: st.error(f"Error on {file.name}: {e}")
            progress_text.empty()
            # Auto-save after analysis
            save_data(st.session_state.projects)

        # --- DISPLAY LOGIC ---
        # Get data for the ACTIVE project
        active_data = st.session_state.projects[st.session_state.active_project]

        if active_data:
            t1, t2, t3 = st.tabs(["🖼️ Card Gallery", "📊 Master Table", "🧠 Synthesis"])
            
            with t1:
                for r in reversed(active_data):
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
                df = pd.DataFrame(active_data)
                st.dataframe(df, use_container_width=True, hide_index=True)
                
                # --- FULL WIDTH EXPORT BUTTON ---
                csv = df.to_csv(index=False).encode('utf-8-sig')
                st.download_button(
                    label="📊 Export as CSV file",
                    data=csv,
                    file_name=f"{st.session_state.active_project}_review.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            
            with t3:
                if len(active_data) > 0:
                    with st.spinner("Performing meta-synthesis..."):
                        evidence_base = ""
                        for r in active_data:
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

    st.markdown('</div>', unsafe_allow_html=True)
