import streamlit as st
import pandas as pd
from pypdf import PdfReader
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
from streamlit_gsheets import GSheetsConnection
import re
import time

# 1. PAGE CONFIGURATION
st.set_page_config(page_title="Literature Review Buddy", page_icon="📚", layout="wide")

# 2. DATABASE CONNECTION (Google Sheets)
conn = st.connection("gsheets", type=GSheetsConnection)

def load_full_library():
    try:
        df = conn.read(ttl=0)
        if df is None or df.empty or 'Project' not in df.columns: return {}
        library = {}
        for _, row in df.iterrows():
            proj = row.get('Project')
            if pd.isna(proj) or not proj: continue
            if proj not in library:
                library[proj] = {"papers": [], "last_accessed": row.get('LastAccessed', 0)}
            if 'Title' in row and pd.notna(row['Title']):
                library[proj]["papers"].append({
                    "#": row.get('#'), "Title": row.get('Title'), "Authors": row.get('Authors'),
                    "Year": row.get('Year'), "Reference": row.get('Reference'), "Summary": row.get('Summary'),
                    "Background": row.get('Background'), "Methodology": row.get('Methodology'),
                    "Context": row.get('Context'), "Findings": row.get('Findings'), "Reliability": row.get('Reliability')
                })
        return library
    except Exception: return {}

def save_full_library(library):
    flat_data = []
    for proj_name, content in library.items():
        if not content.get("papers"):
            flat_data.append({"Project": proj_name, "LastAccessed": content.get("last_accessed", time.time())})
        else:
            for paper in content["papers"]:
                row = {"Project": proj_name, "LastAccessed": content.get("last_accessed", time.time())}
                row.update(paper)
                flat_data.append(row)
    if flat_data:
        try:
            new_df = pd.DataFrame(flat_data)
            conn.update(data=new_df)
        except Exception as e:
            st.error(f"Google Sheets Error: {e}. Ensure the service email is an Editor on the sheet.")

# 3. STYLING (Restored 100% Original Visuals)
st.markdown("""
<style>
[data-testid="stHeader"] { background-color: rgba(255, 255, 255, 0); }
:root { --buddy-green: #18A48C; --buddy-blue: #0000FF; }
[data-testid="block-container"] { padding-top: 0rem !important; }
[data-testid="stTextInput"] div[data-baseweb="input"] { border: 1px solid #d3d3d3 !important; }
[data-testid="stTextInput"] div[data-baseweb="input"]:hover { border-color: var(--buddy-green) !important; }
[data-testid="stTextInput"] div[data-baseweb="input"]:focus-within { border: 2px solid var(--buddy-green) !important; }
div[data-testid="stButton"] button:hover { background-color: var(--buddy-green) !important; color: white !important; }
.icon-btn div[data-testid="stButton"] button { height: 38px !important; width: 38px !important; padding: 0 !important; border: none !important; background: transparent !important; }
.card-del-container div[data-testid="stButton"] button { color: #ff4b4b !important; border: 1px solid #ff4b4b !important; background: transparent !important; font-size: 0.85rem !important; min-width: 140px !important; }
.fixed-header-bg { position: fixed; top: 0; left: 0; width: 100%; height: 4.5rem; background: white; border-bottom: 0.125rem solid #f0f2f6; z-index: 1000; padding-left: 3.75rem; display: flex; align-items: center; }
.fixed-header-text h1 { margin: 0; font-size: 2.2rem; color: #0000FF; }
.upload-pull-up { margin-top: -3.0rem !important; }
.section-title { font-weight: bold; color: #0000FF; margin-top: 1rem; display: block; text-transform: uppercase; font-size: 0.85rem; border-bottom: 0.06rem solid #eee; }
.section-content { display: block; margin-bottom: 10px; line-height: 1.6; color: #333; }
</style>
""", unsafe_allow_html=True)

# 4. AUTHENTICATION
def check_password():
    if "password_correct" not in st.session_state:
        st.markdown('<h1>📚 Literature Review Buddy</h1>', unsafe_allow_html=True)
        pwd = st.text_input("Enter password", type="password")
        if st.button("Unlock"):
            if pwd == "M1chaelL1tRev1ewTool2026!":
                st.session_state["password_correct"] = True
                st.rerun()
            else: st.error("🚫 Access Denied")
        return False
    return True

# 5. MAIN LOGIC
if check_password():
    api_key = st.secrets.get("GEMINI_API_KEY", "AIzaSyCs-N57rUlOl1J8LtwT54b6kLgYnAhmuJg")

    if 'projects' not in st.session_state: st.session_state.projects = load_full_library()
    if 'active_project' not in st.session_state: st.session_state.active_project = None 
    if 'renaming_project' not in st.session_state: st.session_state.renaming_project = None

    if st.session_state.active_project is None:
        # LIBRARY VIEW
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
                    if st.session_state.renaming_project == proj_name:
                        r_col1, r_col2, r_col3 = st.columns([6, 1, 1])
                        with r_col1: new_name_val = st.text_input("Rename", value=proj_name, key=f"r_{proj_name}")
                        with r_col2: 
                            if st.button("✅", key=f"s_{proj_name}"):
                                st.session_state.projects[new_name_val] = st.session_state.projects.pop(proj_name)
                                save_full_library(st.session_state.projects); st.session_state.renaming_project = None; st.rerun()
                        with r_col3:
