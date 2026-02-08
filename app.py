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

# 2. STORAGE LOGIC
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

# 3. STYLING
st.markdown("""
    <style>
    /* Global fixes */
    .stApp a.header-anchor { display: none !important; }
    [data-testid="stDecoration"] { display: none !important; }
    
    /* The Header Container */
    .header-box {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        background-color: white;
        z-index: 999;
        padding: 40px 50px 10px 50px; /* Added top padding to clear browser chrome */
        border-bottom: 2px solid #f0f2f6;
    }

    /* Pushing content down so it doesn't hide under the header */
    .main-content-wrapper {
        margin-top: 130px; 
    }

    /* Title Styling */
    .project-title-text {
        color: #0000FF;
        font-size: 2rem;
        font-weight: bold;
        cursor: pointer;
        margin: 0;
    }

    /* Button Tweak */
    div.stButton > button {
        border-radius: 4px !important;
    }
    
    /* Sidebar spacing */
    [data-testid="stSidebar"] [data-testid="stVerticalBlock"] { gap: 0.3rem !important; }
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
    if 'projects' not in st.session_state: st.session_state.projects = load_data()
    if 'active_project' not in st.session_state: st.session_state.active_project = list(st.session_state.projects.keys())[0]

    # --- SIDEBAR ---
    with st.sidebar:
        st.title("📁 Projects")
        new_name_input = st.text_input("New Review Name")
        if st.button("➕ Create"):
            if new_name_input and new_name_input not in st.session_state.projects:
                st.session_state.projects[new_name_input] = []
                st.session_state.active_project = new_name_input
                save_data(st.session_state.projects)
                st.rerun()
        
        st.divider()
        for proj in list(st.session_state.projects.keys()):
            c1, c2 = st.columns([5, 1])
            active = (proj == st.session_state.active_project)
            if c1.button(f"📍 {proj}" if active else proj, key=f"s_{proj}", use_container_width=True, type="primary" if active else "secondary"):
                st.session_state.active_project = proj
                st.rerun()
            if len(st.session_state.projects) > 1 and c2.button("×", key=f"d_{proj}"):
                del st.session_state.projects[proj]
                if active: st.session_state.active_project = list(st.session_state.projects.keys())[0]
                save_data(st.session_state.projects)
                st.rerun()

    # --- NEW FIXED HEADER ---
    st.markdown('<div class="header-box">', unsafe_allow_html=True)
    h_col1, h_col2 = st.columns([4, 1])
    
    with h_col1:
        if st.session_state.get("editing_now", False):
            new_val = st.text_input("Rename", value=st.session_state.active_project, label_visibility="collapsed")
            if st.button("✅ Save Name"):
                if new_val and new_val != st.session_state.active_project:
                    st.session_state.projects[new_val] = st.session_state.projects.pop(st.session_state.active_project)
                    st.session_state.active_project = new_val
                    save_data(st.session_state.projects)
                st.session_state.editing_now = False
                st.rerun()
        else:
            # Clickable Title
            if st.button(f"📚 {st.session_state.active_project}", help="Click to rename", key="title_trigger", type="secondary"):
                st.session_state.editing_now = True
                st.rerun()
            st.markdown('<p style="color:#18A48C; font-weight: bold; margin:0;">PhD-Level Analysis Mode</p>', unsafe_allow_html=True)

    with h_col2:
        st.write("##")
        if st.button("💾 Save Project"):
            save_data(st.session_state.projects)
            st.toast("Saved!")
    st.markdown('</div>', unsafe_allow_html=True)

    # --- MAIN CONTENT ---
    st.markdown('<div class="main-content-wrapper">', unsafe_allow_html=True)
    
    api_key = st.secrets.get("GEMINI_API_KEY")
    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", google_api_key=api_key, temperature=0.1) if api_key else None

    with st.expander("➕ Upload & Analyse New Papers", expanded=True):
        files = st.file_uploader("Drop PDFs", type="pdf", accept_multiple_files=True)
        if st.button("🔬 Start PhD Analysis"):
            if files and llm:
                for f in files:
                    try:
                        reader = PdfReader(f)
                        text = "".join([p.extract_text() for p in reader.pages]).strip()
                        prompt = f"Analyze: [TITLE], [AUTHORS], [YEAR], [REFERENCE], [SUMMARY], [BACKGROUND], [METHODOLOGY], [CONTEXT], [FINDINGS], [RELIABILITY]. Prose only. TEXT: {text[:30000]}"
                        res = llm.invoke([HumanMessage(content=prompt)]).content
                        
                        def ext(label, next_l=None):
                            p = rf"\[{label}\]:?\s*(.*?)(?=\s*\[{next_l}\]|$)" if next_l else rf"\[{label}\]:?\s*(.*)"
                            m = re.search(p, res, re.DOTALL | re.IGNORECASE)
                            return m.group(1).strip() if m else "Not found."
                        
                        st.session_state.projects[st.session_state.active_project].append({
                            "#": len(st.session_state.projects[st.session_state.active_project]) + 1,
                            "Title": ext("TITLE", "AUTHORS"), "Authors": ext("AUTHORS", "YEAR"), "Year": ext("YEAR", "REFERENCE"),
                            "Reference": ext("REFERENCE", "SUMMARY"), "Summary": ext("SUMMARY", "BACKGROUND"),
                            "Background": ext("BACKGROUND", "METHODOLOGY"), "Methodology": ext("METHODOLOGY", "CONTEXT"),
                            "Context": ext("CONTEXT", "FINDINGS"), "Findings": ext("FINDINGS", "RELIABILITY"),
                            "Reliability": ext("RELIABILITY")
                        })
                    except: st.error(f"Failed to read {f.name}")
                save_data(st.session_state.projects)
                st.rerun()

    data = st.session_state.projects[st.session_state.active_project]
    if data:
        t1, t2, t3 = st.tabs(["🖼️ Card Gallery", "📊 Master Table", "🧠 Synthesis"])
        with t1:
            for r in reversed(data):
                with st.container(border=True):
                    st.subheader(f"Ref {r['#']}: {r['Title']}")
                    st.write(f"**Authors:** {r['Authors']} ({r['Year']})")
                    st.divider()
                    for k, v in [("📝 Summary", r["Summary"]), ("⚙️ Methodology", r["Methodology"]), ("💡 Findings", r["Findings"]), ("🛡️ Reliability", r["Reliability"])]:
                        st.markdown(f"**{k}**")
                        st.write(v)
        with t2:
            st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)
        with t3:
            if len(data) > 1:
                with st.spinner("Synthesizing..."):
                    evidence = "".join([f"P{r['#']}: {r['Findings']}\n" for r in data])
                    synth = llm.invoke([HumanMessage(content=f"Meta-Synthesis: [OVERVIEW], [PATTERNS], [CONTRADICTIONS], [FUTURE_DIRECTIONS].\n{evidence}")]).content
                    st.write(synth)

    st.markdown('</div>', unsafe_allow_html=True)
