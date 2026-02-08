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
                return data if data else {}
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
    :root { --buddy-green: #18A48C; --buddy-blue: #0000FF; }
    
    .sticky-wrapper { position: fixed; top: 0; left: 0; width: 100%; background-color: white; z-index: 1000; padding: 10px 50px 10px 50px; border-bottom: 2px solid #f0f2f6; }
    .main-content { margin-top: 80px; }
    
    /* Buttons Styling */
    div.stButton > button:first-child, div.stDownloadButton > button:first-child {
        width: 100% !important; color: var(--buddy-green) !important; border: 1px solid var(--buddy-green) !important; font-weight: bold !important; background-color: transparent !important;
    }
    div.stButton > button:hover, div.stDownloadButton > button:hover { background-color: var(--buddy-green) !important; color: white !important; }
    
    /* VERTICAL ALIGNMENT FIX for Library List */
    [data-testid="column"] {
        display: flex !important;
        align-items: center !important;
    }

    .del-btn > div > button {
        border: none !important;
        color: #ff4b4b !important;
        background: transparent !important;
        padding: 0px !important;
        line-height: 1 !important;
        height: 38px !important;
    }
    .del-btn > div > button:hover { color: #b30000 !important; background: transparent !important; }

    .section-title { font-weight: bold; color: #0000FF; margin-top: 15px; display: block; text-transform: uppercase; font-size: 0.85rem; border-bottom: 1px solid #eee; }
    .section-content { display: block; margin-bottom: 10px; line-height: 1.6; color: #333; }
    
    .paper-del-btn > div > button {
        color: #ff4b4b !important; border: 1px solid #ff4b4b !important; font-size: 0.8rem !important; margin-top: 20px !important;
    }
    </style>
    """, unsafe_allow_html=True)

# 4. AUTHENTICATION
def check_password():
    correct_password = st.secrets.get("APP_PASSWORD")
    if "password_correct" not in st.session_state:
        st.markdown('<h1 style="color:#0000FF; text-align:center;">📚 Literature Review Buddy</h1>', unsafe_allow_html=True)
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
    if 'view' not in st.session_state:
        st.session_state.view = "library"

    # --- VIEW: PROJECT LIBRARY (HOME) ---
    if st.session_state.view == "library":
        st.markdown('<h1 style="color:#0000FF;">📂 Project Library</h1>', unsafe_allow_html=True)
        
        with st.expander("➕ Create New Project", expanded=True):
            new_name = st.text_input("Project Name")
            if st.button("Create"):
                if new_name and new_name not in st.session_state.projects:
                    st.session_state.projects[new_name] = []
                    save_data(st.session_state.projects)
                    st.rerun()

        st.divider()
        
        if not st.session_state.projects:
            st.info("Your library is empty. Create a project to get started.")
        else:
            for proj in list(st.session_state.projects.keys()):
                cols = st.columns([5, 1])
                if cols[0].button(f"📖 {proj}", key=f"open_{proj}", use_container_width=True):
                    st.session_state.active_project = proj
                    st.session_state.view = "project"
                    st.rerun()
                
                with cols[1]:
                    st.markdown('<div class="del-btn">', unsafe_allow_html=True)
                    if st.button("×", key=f"del_proj_{proj}", help="Delete Project"):
                        del st.session_state.projects[proj]
                        save_data(st.session_state.projects)
                        st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)

    # --- VIEW: INDIVIDUAL PROJECT ---
    elif st.session_state.view == "project":
        proj_name = st.session_state.active_project
        
        # Header with Back and Save
        st.markdown('<div class="sticky-wrapper">', unsafe_allow_html=True)
        h_col1, h_col2, h_col3 = st.columns([1, 4, 1])
        with h_col1:
            if st.button("⬅️ Library"):
                st.session_state.view = "library"
                st.rerun()
        with h_col2:
            st.markdown(f'<h1 style="margin:0; font-size: 1.8rem; color:#0000FF;">📚 {proj_name}</h1>', unsafe_allow_html=True)
        with h_col3:
            if st.button("💾 Save"):
                save_data(st.session_state.projects)
                st.toast("Saved!", icon="✅")
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="main-content">', unsafe_allow_html=True)
        
        api_key = st.secrets.get("GEMINI_API_KEY")
        llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", google_api_key=api_key, temperature=0.1) if api_key else None

        with st.expander("🔬 Analyse New Papers"):
            files = st.file_uploader("Upload PDFs", type="pdf", accept_multiple_files=True)
            if st.button("Start Analysis", use_container_width=True):
                if files and llm:
                    for f in files:
                        try:
                            reader = PdfReader(f)
                            text = "".join([p.extract_text() for p in reader.pages]).strip()
                            prompt = f"Analyze as PhD: [TITLE], [AUTHORS], [YEAR], [REFERENCE], [SUMMARY], [BACKGROUND], [METHODOLOGY], [CONTEXT], [FINDINGS], [RELIABILITY]. TEXT: {text[:30000]}"
                            res = llm.invoke([HumanMessage(content=prompt)]).content
                            
                            def ext(label, next_l=None):
                                p = rf"\[{label}\]:?\s*(.*?)(?=\s*\[{next_l}\]|$)" if next_l else rf"\[{label}\]:?\s*(.*)"
                                m = re.search(p, res, re.DOTALL | re.IGNORECASE)
                                return m.group(1).strip() if m else "Not found."

                            st.session_state.projects[proj_name].append({
                                "id": str(os.urandom(4).hex()),
                                "Title": ext("TITLE", "AUTHORS"), "Authors": ext("AUTHORS", "YEAR"), "Year": ext("YEAR", "REFERENCE"),
                                "Summary": ext("SUMMARY", "BACKGROUND"), "Methodology": ext("METHODOLOGY", "CONTEXT"), "Findings": ext("FINDINGS", "RELIABILITY")
                            })
                        except: st.error(f"Error on {f.name}")
                    save_data(st.session_state.projects)
                    st.rerun()

        papers = st.session_state.projects[proj_name]
        if papers:
            t1, t2 = st.tabs(["🖼️ Cards", "📊 Table"])
            with t1:
                for r in reversed(papers):
                    with st.container(border=True):
                        st.subheader(r['Title'])
                        for k, v in [("📝 Summary", r["Summary"]), ("⚙️ Methodology", r["Methodology"]), ("💡 Findings", r["Findings"])]:
                            st.markdown(f"**{k}**")
                            st.write(v)
                        
                        st.markdown('<div class="paper-del-btn">', unsafe_allow_html=True)
                        if st.button("🗑️ Delete Analysis", key=f"del_paper_{r['id']}"):
                            st.session_state.projects[proj_name] = [p for p in papers if p['id'] != r['id']]
                            save_data(st.session_state.projects)
                            st.rerun()
                        st.markdown('</div>', unsafe_allow_html=True)
            with t2:
                st.dataframe(pd.DataFrame(papers), use_container_width=True)

        st.markdown('</div>', unsafe_allow_html=True)
