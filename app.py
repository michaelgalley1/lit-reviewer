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
    [data-testid="stHeader"] { background-color: rgba(255, 255, 255, 0); }
    :root { --buddy-green: #18A48C; --buddy-blue: #0000FF; }
    
    /* REMOVE DEFAULT PADDING */
    [data-testid="block-container"] {
        padding-top: 0rem !important;
        margin-top: 0rem !important;
    }

    /* FIXED HEADER CONTAINER */
    .sticky-wrapper { 
        position: fixed; 
        top: 0; 
        left: 0; 
        width: 100%; 
        background-color: white; 
        z-index: 1000; 
        padding: 15px 50px 10px 50px; 
        border-bottom: 2px solid #f0f2f6; 
        height: auto;
    }
    
    /* App Title in Header */
    .app-brand {
        font-size: 1.2rem;
        font-weight: bold;
        color: #333;
        margin-bottom: 8px;
    }

    /* Main Content Spacing - Adjusted to pull content up */
    .main-content { 
        margin-top: 110px; /* Reduced from 140px to close the gap */
    }
    
    /* RIGHT ALIGN SAVE BUTTON */
    /* Forces the second column in the header row to align right */
    .header-row [data-testid="column"]:nth-of-type(2) {
        display: flex;
        justify-content: flex-end !important;
        align-items: center;
    }
    
    /* Save Button Styling */
    .save-btn-container button {
        border: none !important;
        font-size: 1.8rem !important;
        padding: 0px !important;
        background: transparent !important;
        line-height: 1;
    }
    .save-btn-container button:hover {
        background: transparent !important;
        transform: scale(1.1);
    }
    
    /* General Button Styling */
    div.stButton > button:first-child, div.stDownloadButton > button:first-child {
        width: 100% !important; color: var(--buddy-green) !important; border: 1px solid var(--buddy-green) !important; font-weight: bold !important; background-color: transparent !important;
    }
    div.stButton > button:hover, div.stDownloadButton > button:hover { background-color: var(--buddy-green) !important; color: white !important; }
    
    /* SIDEBAR SPACING */
    [data-testid="stSidebar"] [data-testid="stVerticalBlock"] {
        gap: 0.15rem !important;
    }
    [data-testid="stSidebar"] [data-testid="stVerticalBlock"] > div:has(input) {
        margin-bottom: 0.2rem !important;
    }
    
    .del-btn > div > button {
        border: none !important;
        color: #ff4b4b !important;
        background: transparent !important;
        padding: 0px !important;
        line-height: 1 !important;
        height: 38px !important; 
    }
    .del-btn > div > button:hover {
        color: #b30000 !important;
        background: transparent !important;
    }

    .section-title { font-weight: bold; color: #0000FF; margin-top: 15px; display: block; text-transform: uppercase; font-size: 0.85rem; border-bottom: 1px solid #eee; }
    .section-content { display: block; margin-bottom: 10px; line-height: 1.6; color: #333; }
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
        # 4. CHANGED EMOJI TO 🗂️
        st.title("🗂️ Research Manager")
        new_proj_name = st.text_input("Name for New Review", placeholder="e.g. AI Ethics 2026", label_visibility="collapsed")
        if st.button("➕ Create Project"):
            if new_proj_name and new_proj_name not in st.session_state.projects:
                st.session_state.projects[new_proj_name] = []
                st.session_state.active_project = new_proj_name
                save_data(st.session_state.projects)
                st.rerun()
        
        st.divider()
        st.subheader("Your Projects")
        for proj in list(st.session_state.projects.keys()):
            cols = st.columns([4, 1])
            is_active = (proj == st.session_state.active_project)
            label = f"📍 {proj}" if is_active else proj
            if cols[0].button(label, key=f"sel_{proj}", use_container_width=True, type="primary" if is_active else "secondary"):
                st.session_state.active_project = proj
                st.rerun()
            if len(st.session_state.projects) > 1:
                st.markdown('<div class="del-btn">', unsafe_allow_html=True)
                if cols[1].button("×", key=f"del_{proj}", help=f"Delete {proj}"):
                    del st.session_state.projects[proj]
                    if is_active:
                        st.session_state.active_project = list(st.session_state.projects.keys())[0]
                    save_data(st.session_state.projects)
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

    # --- HEADER (Sticky) ---
    st.markdown('<div class="sticky-wrapper">', unsafe_allow_html=True)
    # 1. FROZEN TITLE AT TOP
    st.markdown('<div class="app-brand">📚 Literature Review Buddy</div>', unsafe_allow_html=True)
    
    # Using a container class 'header-row' to target columns with CSS
    st.markdown('<div class="header-row">', unsafe_allow_html=True)
    head_col1, head_col2 = st.columns([4, 1])
    
    with head_col1:
        st.markdown(f'<h1 style="margin:0; font-size: 2rem; color:#0000FF;">{st.session_state.active_project}</h1>', unsafe_allow_html=True)
        st.markdown('<p style="color:#18A48C; margin:0; font-weight: bold; font-size: 0.9rem;">PhD-Level Analysis Mode</p>', unsafe_allow_html=True)
    
    with head_col2:
        # 3. RIGHT ALIGNED SAVE BUTTON
        st.markdown('<div class="save-btn-container">', unsafe_allow_html=True)
        if st.button("💾", help="Save Progress"):
            save_data(st.session_state.projects)
            st.toast("Project Saved!", icon="✅")
        st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True) # End header-row
    st.markdown('</div>', unsafe_allow_html=True) # End sticky-wrapper

    # --- MAIN CONTENT ---
    # 2. REDUCED GAP (margin-top handled in CSS)
    st.markdown('<div class="main-content">', unsafe_allow_html=True)
    
    api_key = st.secrets.get("GEMINI_API_KEY")
    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", google_api_key=api_key, temperature=0.1) if api_key else None

    # --- UPLOAD SECTION ---
    with st.expander("Upload and Analyse Papers", expanded=True):
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
                    prompt = f"Analyze as PhD Candidate: [TITLE], [AUTHORS], [YEAR], [REFERENCE], [SUMMARY], [BACKGROUND], [METHODOLOGY], [CONTEXT], [FINDINGS], [RELIABILITY]. Sophisticated prose, no bolding. TEXT: {text[:30000]}"
                    res = llm.invoke([HumanMessage(content=prompt)]).content
                    res = re.sub(r'\*', '', res) 

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
                except Exception as e: st.error(f"Error: {e}")
            progress_text.empty()
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
                        st.markdown(f'<span class="section-title">{k}</span><span class="section-content">{v}</span>', unsafe_allow_html=True)
        with t2:
            df = pd.DataFrame(current_data)
            st.dataframe(df, use_container_width=True, hide_index=True)
            st.download_button("📊 Export Project CSV", data=df.to_csv(index=False).encode('utf-8-sig'), file_name=f"{st.session_state.active_project}.csv", use_container_width=True)
        with t3:
            if len(current_data) > 0:
                with st.spinner("Synthesizing..."):
                    evidence = "".join([f"P{r['#']}: {r['Findings']}\n" for r in current_data])
                    synth_res = llm.invoke([HumanMessage(content=f"Meta-Synthesis: Use [OVERVIEW], [PATTERNS], [CONTRADICTIONS], [FUTURE_DIRECTIONS]. No bolding. TEXT:\n{evidence}")]).content
                    st.write(synth_res)

    st.markdown('</div>', unsafe_allow_html=True)
