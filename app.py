import streamlit as st
import pandas as pd
from pypdf import PdfReader
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
import re
import json
import os

# 1. PAGE CONFIGURATION
st.set_page_config(page_title="Literature Review Buddy", page_icon="📚", layout="wide")

# 2. STORAGE SETUP
DB_FILE = "buddy_data.json"

def load_data():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f:
                return json.load(f)
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

/* Home Page Card Styling */
div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlock"] {
    /* General fix for spacing */
}

/* Button Styling */
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

# 5. MAIN LOGIC
if check_password():
    api_key = st.secrets.get("GEMINI_API_KEY")

    # Initialize Session State
    if 'projects' not in st.session_state:
        st.session_state.projects = load_data()
    if 'active_project' not in st.session_state:
        st.session_state.active_project = None # Represents "Home Page" mode

    # ==========================================
    # VIEW 1: HOME PAGE (Project Selection)
    # ==========================================
    if st.session_state.active_project is None:
        
        # Header
        st.markdown(f'''
        <div style="padding: 20px 0px;">
            <h1 style="margin:0; font-size: 2.2rem; color:#0000FF;">🗂️ Project Library</h1>
            <p style="color:#18A48C; font-weight: bold;">Select an existing review or start a new one.</p>
        </div>
        ''', unsafe_allow_html=True)

        # Create New Project Section
        with st.container(border=True):
            c1, c2 = st.columns([4, 1])
            new_name = c1.text_input("New Project Name", placeholder="e.g. AI Ethics 2026", label_visibility="collapsed")
            if c2.button("➕ Create New"):
                if new_name and new_name not in st.session_state.projects:
                    st.session_state.projects[new_name] = []
                    save_data(st.session_state.projects)
                    st.session_state.active_project = new_name
                    st.rerun()
                elif new_name in st.session_state.projects:
                    st.error("Project already exists.")

        st.write("###") # Spacer

        # Project Cards Grid
        projects = list(st.session_state.projects.keys())
        
        if not projects:
            st.info("No projects found. Create one above to get started!")
        else:
            # Create a grid of cards (3 per row)
            cols = st.columns(3)
            for i, proj_name in enumerate(projects):
                with cols[i % 3]:
                    # Card Container
                    with st.container(border=True):
                        paper_count = len(st.session_state.projects[proj_name])
                        st.subheader(f"📍 {proj_name}")
                        st.caption(f"📚 {paper_count} Papers Analyzed")
                        
                        b1, b2 = st.columns([1, 1])
                        if b1.button("Open", key=f"open_{proj_name}"):
                            st.session_state.active_project = proj_name
                            st.rerun()
                        
                        if b2.button("Delete", key=f"del_{proj_name}"):
                            del st.session_state.projects[proj_name]
                            save_data(st.session_state.projects)
                            st.rerun()

    # ==========================================
    # VIEW 2: ANALYSIS DASHBOARD (The Original Tool)
    # ==========================================
    else:
        # 1. NAVIGATION BAR (Go Back)
        with st.sidebar:
            if st.button("⬅️ Back to Library"):
                st.session_state.active_project = None
                st.rerun()
            st.divider()
            st.write(f"**Current Project:**\n\n{st.session_state.active_project}")

        # 2. MAIN HEADER (Restored from your version)
        st.markdown(f'''
        <div class="sticky-wrapper">
            <h1 style="margin:0; font-size: 1.8rem; color:#0000FF;">📚 Literature Review Buddy</h1>
            <p style="color:#18A48C; margin-bottom:5px; font-weight: bold;">{st.session_state.active_project} | PhD-Level Research Assistant</p>
        </div>
        ''', unsafe_allow_html=True)

        with st.container():
            st.write("##")
            st.markdown('<div class="main-content">', unsafe_allow_html=True)
            llm = None
            if api_key:
                llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", google_api_key=api_key, temperature=0.1)

            uploaded_files = st.file_uploader("Upload academic papers (PDF)", type="pdf", accept_multiple_files=True)
            run_review = st.button("🔬 Analyse paper", use_container_width=True)

            if uploaded_files and llm and run_review:
                progress_text = st.empty()
                # Use a temporary set for this session's uploads to prevent immediate duplicates
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

                        # APPEND TO ACTIVE PROJECT
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
                        st.session_state.session_uploads.add(file.name)
                        
                        # AUTO SAVE
                        save_data(st.session_state.projects)
                        
                    except Exception as e: st.error(f"Error on {file.name}: {e}")
                progress_text.empty()
                st.rerun() # Refresh to show new data

            # GET DATA FOR ACTIVE PROJECT
            current_data = st.session_state.projects[st.session_state.active_project]

            if current_data:
                t1, t2, t3 = st.tabs(["🖼️ Card Gallery", "📊 Master Table", "🧠 Synthesis"])
                with t1:
                    for r in reversed(current_data):
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
                    df = pd.DataFrame(current_data)
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
                    if len(current_data) > 0:
                        with st.spinner("Performing meta-synthesis..."):
                            evidence_base = ""
                            for r in current_data:
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
