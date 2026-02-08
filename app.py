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

# 2. STORAGE LOGIC (JSON)
DB_FILE = "buddy_library.json"

def load_data():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f:
                return json.load(f)
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
    :root { --buddy-green: #18A48C; --buddy-blue: #0000FF; }
    [data-testid="stTextInput"] div[data-baseweb="input"] { border: 1px solid #d3d3d3 !important; }
    .sticky-wrapper { position: fixed; top: 0; left: 0; width: 100%; background-color: white; z-index: 1000; padding: 10px 50px 0px 50px; border-bottom: 2px solid #f0f2f6; }
    .main-content { margin-top: -30px; }
    div.stButton > button:first-child, div.stDownloadButton > button:first-child {
        width: 100% !important; color: var(--buddy-green) !important; border: 2px solid var(--buddy-green) !important; font-weight: bold !important; background-color: transparent !important;
    }
    div.stButton > button:hover, div.stDownloadButton > button:hover { background-color: var(--buddy-green) !important; color: white !important; }
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
        st.markdown('<h1 style="color:#0000FF;">📚 Literature Review Buddy</h1>', unsafe_allow_html=True)
        pwd = st.text_input("Enter password", type="password")
        if st.button("Unlock Tool"):
            if pwd == correct_password:
                st.session_state["password_correct"] = True
                st.rerun()
            else: st.error("🚫 Access Denied")
        return False
    return True

if check_password():
    if 'projects' not in st.session_state:
        st.session_state.projects = load_data()
    if 'active_project' not in st.session_state:
        st.session_state.active_project = list(st.session_state.projects.keys())[0]

    # --- SIDEBAR ---
    with st.sidebar:
        st.title("📁 Research Manager")
        
        st.session_state.active_project = st.selectbox(
            "Select Project", 
            options=list(st.session_state.projects.keys())
        )
        
        st.divider()
        new_proj_name = st.text_input("New Project Name")
        if st.button("➕ Create Project"):
            if new_proj_name and new_proj_name not in st.session_state.projects:
                st.session_state.projects[new_proj_name] = []
                st.session_state.active_project = new_proj_name
                save_data(st.session_state.projects)
                st.rerun()

        st.divider()
        if st.button("💾 Save All Progress"):
            save_data(st.session_state.projects)
            st.success("Library saved successfully!")

    # --- MAIN UI ---
    st.markdown(f'''
        <div class="sticky-wrapper">
            <h1 style="margin:0; font-size: 1.8rem; color:#0000FF;">📚 {st.session_state.active_project}</h1>
            <p style="color:#18A48C; margin-bottom:5px; font-weight: bold;">PhD-Level Analysis Mode</p>
        </div>
    ''', unsafe_allow_html=True)

    st.write("##")
    st.markdown('<div class="main-content">', unsafe_allow_html=True)
    
    api_key = st.secrets.get("GEMINI_API_KEY")
    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", google_api_key=api_key, temperature=0.1) if api_key else None

    uploaded_files = st.file_uploader("Upload papers (PDF)", type="pdf", accept_multiple_files=True)
    run_review = st.button("🔬 Analyse paper", use_container_width=True)

    if uploaded_files and llm and run_review:
        progress_text = st.empty()
        existing_titles = {paper['Title'].lower() for paper in st.session_state.projects[st.session_state.active_project]}
        
        for file in uploaded_files:
            progress_text.text(f"📖 Reviewing: {file.name}...")
            try:
                reader = PdfReader(file) 
                text = "".join([p.extract_text() for p in reader.pages if p.extract_text()]).strip()
                
                # REINSTATED VERSION 1 PROMPT
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

                # REINSTATED VERSION 1 EXTRACTION LOGIC
                def ext(label, next_l=None):
                    p = rf"\[{label}\]:?\s*(.*?)(?=\s*\[{next_l}\]|$)" if next_l else rf"\[{label}\]:?\s*(.*)"
                    m = re.search(p, res, re.DOTALL | re.IGNORECASE)
                    return m.group(1).strip() if m else "Not found."

                title = ext("TITLE", "AUTHORS")
                if title.lower() not in existing_titles:
                    st.session_state.projects[st.session_state.active_project].append({
                        "#": len(st.session_state.projects[st.session_state.active_project]) + 1,
                        "Title": title,
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
                    existing_titles.add(title.lower())
            except Exception as e: st.error(f"Error on {file.name}: {e}")
        progress_text.empty()
        save_data(st.session_state.projects)

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
            st.download_button("📊 Export Project CSV", data=df.to_csv(index=False).encode('utf-8-sig'), file_name=f"{st.session_state.active_project}.csv", use_container_width=True)

        with t3:
            if len(current_data) > 0:
                with st.spinner("Synthesizing..."):
                    evidence_base = "".join([f"Paper {r['#']} ({r['Year']}): Findings: {r['Findings']}. Methodology: {r['Methodology']}\n\n" for r in current_data])
                    synth_prompt = f"Meta-Synthesis: Use [OVERVIEW], [PATTERNS], [CONTRADICTIONS], [FUTURE_DIRECTIONS]. No bolding.\n\nEvidence Base:\n{evidence_base}"
                    raw_synth = llm.invoke([HumanMessage(content=synth_prompt)]).content
                    clean_synth = re.sub(r'\*', '', raw_synth)

                    def get_synth(label, next_l=None):
                        p = rf"\[{label}\]:?\s*(.*?)(?=\s*\[{next_l}\]|$)" if next_l else rf"\[{label}\]:?\s*(.*)"
                        m = re.search(p, clean_synth, re.DOTALL | re.IGNORECASE)
                        return m.group(1).strip() if m else "Detail not found."

                    st.markdown("### 🎯 Executive Overview"); st.write(get_synth("OVERVIEW", "PATTERNS"))
                    st.markdown("### 📈 Cross-Study Patterns"); st.write(get_synth("PATTERNS", "CONTRADICTIONS"))
                    st.markdown("### ⚖️ Conflicts & Contradictions"); st.write(get_synth("CONTRADICTIONS", "FUTURE_DIRECTIONS"))
                    st.markdown("### 🚀 Future Research Directions"); st.write(get_synth("FUTURE_DIRECTIONS"))

    st.markdown('</div>', unsafe_allow_html=True)
