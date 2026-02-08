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
    .stApp a.header-anchor { display: none !important; }
    [data-testid="stDecoration"] { display: none !important; }
    :root { --buddy-green: #18A48C; --buddy-blue: #0000FF; }
    
    /* Header Container */
    .header-box {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        background-color: white;
        z-index: 999;
        padding: 50px 50px 15px 50px;
        border-bottom: 2px solid #f0f2f6;
    }

    /* Content Clearance */
    .main-content-wrapper { margin-top: 140px; }

    /* Title Button Styling - Large Blue Font */
    .rename-trigger button {
        background: transparent !important;
        border: none !important;
        padding: 0 !important;
        text-align: left !important;
        font-size: 2.2rem !important;
        font-weight: bold !important;
        color: #0000FF !important;
        box-shadow: none !important;
        line-height: 1.2 !important;
    }

    /* Save Button Alignment */
    .save-container {
        display: flex;
        justify-content: flex-end;
        align-items: center;
        height: 100%;
    }

    /* Sidebar Spacing Restored */
    [data-testid="stSidebar"] [data-testid="stVerticalBlock"] { gap: 0.4rem !important; }
    
    div.stButton > button:first-child {
        width: 100% !important; color: var(--buddy-green) !important; border: 1px solid var(--buddy-green) !important; font-weight: bold !important;
    }
    .del-btn > div > button { border: none !important; color: #ff4b4b !important; background: transparent !important; padding: 0px !important; height: 38px !important; }
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

    # --- SIDEBAR (RESTORED TO PREVIOUS LIST STYLE) ---
    with st.sidebar:
        st.title("📁 Research Manager")
        new_proj_name = st.text_input("Name for New Review", placeholder="e.g. AI Ethics 2026")
        if st.button("➕ Create Project"):
            if new_proj_name and new_proj_name not in st.session_state.projects:
                st.session_state.projects[new_proj_name] = []
                st.session_state.active_project = new_proj_name
                save_data(st.session_state.projects)
                st.rerun()
        
        st.divider()
        st.subheader("Your Projects")
        for proj in list(st.session_state.projects.keys()):
            cols = st.columns([5, 1])
            is_active = (proj == st.session_state.active_project)
            if cols[0].button(f"📍 {proj}" if is_active else proj, key=f"sel_{proj}", use_container_width=True, type="primary" if is_active else "secondary"):
                st.session_state.active_project = proj
                st.rerun()
            if len(st.session_state.projects) > 1:
                with cols[1]:
                    st.markdown('<div class="del-btn">', unsafe_allow_html=True)
                    if st.button("×", key=f"del_{proj}"):
                        del st.session_state.projects[proj]
                        if is_active: st.session_state.active_project = list(st.session_state.projects.keys())[0]
                        save_data(st.session_state.projects)
                        st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)

    # --- HEADER ---
    st.markdown('<div class="header-box">', unsafe_allow_html=True)
    head_col1, head_col2 = st.columns([3, 1]) # Column layout for alignment
    
    with head_col1:
        if st.session_state.get("editing_title", False):
            new_val = st.text_input("Rename", value=st.session_state.active_project, label_visibility="collapsed")
            if st.button("✅ Save"):
                if new_val and new_val != st.session_state.active_project:
                    st.session_state.projects[new_val] = st.session_state.projects.pop(st.session_state.active_project)
                    st.session_state.active_project = new_val
                    save_data(st.session_state.projects)
                st.session_state.editing_title = False
                st.rerun()
        else:
            st.markdown('<div class="rename-trigger">', unsafe_allow_html=True)
            if st.button(f"{st.session_state.active_project}"):
                st.session_state.editing_title = True
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
            st.markdown('<p style="color:#18A48C; margin:0; font-weight: bold; font-size:0.9rem;">PhD-Level Analysis Mode</p>', unsafe_allow_html=True)

    with head_col2:
        st.markdown('<div class="save-container">', unsafe_allow_html=True)
        if st.button("💾 Save Project"):
            save_data(st.session_state.projects)
            st.toast("Saved!", icon="✅")
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # --- CONTENT ---
    st.markdown('<div class="main-content-wrapper">', unsafe_allow_html=True)
    
    api_key = st.secrets.get("GEMINI_API_KEY")
    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", google_api_key=api_key, temperature=0.1) if api_key else None

    with st.expander("➕ Upload & Analyse New Papers", expanded=True):
        uploaded_files = st.file_uploader("Drop PDFs here", type="pdf", accept_multiple_files=True)
        if st.button("🔬 Start PhD Analysis", use_container_width=True):
            if uploaded_files and llm:
                for file in uploaded_files:
                    try:
                        reader = PdfReader(file) 
                        text = "".join([p.extract_text() for p in reader.pages]).strip()
                        prompt = f"Analyze as PhD: [TITLE], [AUTHORS], [YEAR], [REFERENCE], [SUMMARY], [BACKGROUND], [METHODOLOGY], [CONTEXT], [FINDINGS], [RELIABILITY]. Prose only. TEXT: {text[:30000]}"
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
                    except: st.error(f"Error reading {file.name}")
                save_data(st.session_state.projects)
                st.rerun()

    current_data = st.session_state.projects[st.session_state.active_project]
    if current_data:
        t1, t2, t3 = st.tabs(["🖼️ Card Gallery", "📊 Master Table", "🧠 Synthesis"])
        with t1:
            for r in reversed(current_data):
                with st.container(border=True):
                    cr, ct = st.columns([1, 12]); cr.metric("Ref", r['#']); ct.subheader(r['Title'])
                    st.divider()
                    for k, v in [("📝 Summary", r["Summary"]), ("⚙️ Methodology", r["Methodology"]), ("💡 Findings", r["Findings"]), ("🛡️ Reliability", r["Reliability"])]:
                        st.markdown(f"**{k}**")
                        st.write(v)
        with t2:
            st.dataframe(pd.DataFrame(current_data), use_container_width=True, hide_index=True)
        with t3:
            if len(current_data) > 1:
                with st.spinner("Synthesizing..."):
                    evidence = "".join([f"P{r['#']}: {r['Findings']}\n" for r in current_data])
                    synth_res = llm.invoke([HumanMessage(content=f"Meta-Synthesis: [OVERVIEW], [PATTERNS], [CONTRADICTIONS], [FUTURE_DIRECTIONS].\n{evidence}")]).content
                    st.write(synth_res)

    st.markdown('</div>', unsafe_allow_html=True)
