import streamlit as st
import pandas as pd
from pypdf import PdfReader
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
import re
import json
import os
import time

# 1. PAGE CONFIGURATION
st.set_page_config(page_title="Literature Review Buddy", page_icon="📚", layout="wide")

# 2. STORAGE SETUP
DB_FILE = "buddy_projects.json"

def load_data():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f:
                data = json.load(f)
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

# 3. STYLING
st.markdown("""
<style>
[data-testid="stHeader"] { background-color: rgba(255, 255, 255, 0); }
:root { --buddy-green: #18A48C; --buddy-blue: #0000FF; }
[data-testid="block-container"] { padding-top: 0rem !important; }

/* TAB STYLING - Green underline & Green text */
button[data-baseweb="tab"] { background-color: transparent !important; }
button[data-baseweb="tab"]:hover { color: var(--buddy-green) !important; }
button[data-baseweb="tab"][aria-selected="true"] { color: var(--buddy-green) !important; border-bottom-color: var(--buddy-green) !important; }
div[data-baseweb="tab-highlight"] { background-color: transparent !important; visibility: hidden !important; }

/* INPUT & BUTTON HOVER */
[data-testid="stTextInput"] div[data-baseweb="input"]:hover { border-color: var(--buddy-green) !important; }
div[data-testid="stButton"] button:hover { background-color: var(--buddy-green) !important; color: white !important; border-color: var(--buddy-green) !important; }

.section-title { font-weight: bold; color: #0000FF; margin-top: 1rem; display: block; text-transform: uppercase; font-size: 0.85rem; border-bottom: 0.06rem solid #eee; }
.section-content { display: block; margin-bottom: 10px; line-height: 1.6; color: #333; }
.fixed-header-bg { position: fixed; top: 0; left: 0; width: 100%; height: 4.5rem; background: white; border-bottom: 0.125rem solid #f0f2f6; z-index: 1000; padding-left: 3.75rem; display: flex; align-items: center; }
.fixed-header-text h1 { margin: 0; font-size: 2.2rem; color: #0000FF; }
.upload-pull-up { margin-top: -3.0rem !important; padding-bottom: 1rem; }
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

    if 'projects' not in st.session_state: st.session_state.projects = load_data()
    if 'active_project' not in st.session_state: st.session_state.active_project = None 
    if 'renaming_project' not in st.session_state: st.session_state.renaming_project = None

    if st.session_state.active_project is None:
        # LIBRARY VIEW
        st.markdown('<div><h1 style="color:#0000FF;">🗂️ Project Library</h1><p style="color:#18A48C; font-weight: bold;">Select an existing review or start a new one</p></div>', unsafe_allow_html=True)
        with st.container(border=True):
            c1, c2 = st.columns([4, 1])
            new_name = c1.text_input("New Project Name", placeholder="e.g. AI Ethics 2026", label_visibility="collapsed")
            if c2.button("➕ Create Project", use_container_width=True):
                if new_name and new_name not in st.session_state.projects:
                    st.session_state.projects[new_name] = {"papers": [], "last_accessed": time.time()}
                    save_data(st.session_state.projects)
                    st.session_state.active_project = new_name; st.rerun()

        projects = list(st.session_state.projects.keys())
        for proj_name in sorted(projects, key=lambda k: st.session_state.projects[k].get("last_accessed", 0), reverse=True):
            with st.container(border=True):
                col_name, col_spacer, col_open = st.columns([6, 2, 2])
                with col_name:
                    p_count = len(st.session_state.projects[proj_name]["papers"])
                    st.markdown(f"**{proj_name}** ({p_count} Papers)", unsafe_allow_html=True)
                with col_open:
                    if st.button("Open ➡️", key=f"op_{proj_name}"):
                        st.session_state.active_project = proj_name; st.rerun()

    else:
        # PROJECT VIEW
        st.markdown(f'<div class="fixed-header-bg"><div class="fixed-header-text"><h1>{st.session_state.active_project}</h1></div></div>', unsafe_allow_html=True)
        st.markdown('<div class="upload-pull-up">', unsafe_allow_html=True)
        
        llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", google_api_key=api_key, temperature=0.1)
        uploaded_files = st.file_uploader("Upload academic papers (PDF)", type="pdf", accept_multiple_files=True)
        
        # We use a session state set to track uploads so we don't re-analyse the same file accidentally
        if 'processed_this_session' not in st.session_state:
            st.session_state.processed_this_session = set()

        if st.button("🔬 Analyse paper", use_container_width=True):
            if uploaded_files:
                progress_container = st.empty()
                for file in uploaded_files:
                    if file.name in st.session_state.processed_this_session:
                        continue
                        
                    progress_container.info(f"📖 Analysing: {file.name}...")
                    try:
                        reader = PdfReader(file)
                        text = "".join([p.extract_text() for p in reader.pages[:10] if p.extract_text()]).strip()
                        
                        prompt = (
                            "Act as PhD Supervisor. Extract ONLY these labels in brackets followed by text: "
                            "[TITLE], [AUTHORS], [YEAR], [REFERENCE], [SUMMARY], [BACKGROUND], [METHODOLOGY], [CONTEXT], [FINDINGS], [RELIABILITY]. "
                            "No bold. No stars. Text: " + text[:30000]
                        )
                        
                        res = llm.invoke([HumanMessage(content=prompt)]).content
                        res = re.sub(r'\*', '', res)
                        
                        def ext(label):
                            p = rf"\[{label}\]\s*:?\s*(.*?)(?=\s*\[|$)"
                            m = re.search(p, res, re.DOTALL | re.IGNORECASE)
                            return m.group(1).strip() if m else "Not explicitly stated."

                        new_paper = {
                            "#": len(st.session_state.projects[st.session_state.active_project]["papers"]) + 1,
                            "Title": ext("TITLE"), "Authors": ext("AUTHORS"), "Year": ext("YEAR"),
                            "Reference": ext("REFERENCE"), "Summary": ext("SUMMARY"),
                            "Background": ext("BACKGROUND"), "Methodology": ext("METHODOLOGY"),
                            "Context": ext("CONTEXT"), "Findings": ext("FINDINGS"),
                            "Reliability": ext("RELIABILITY")
                        }
                        
                        st.session_state.projects[st.session_state.active_project]["papers"].append(new_paper)
                        st.session_state.processed_this_session.add(file.name)
                        save_data(st.session_state.projects)
                    except Exception as e:
                        st.error(f"Error with {file.name}: {e}")
                
                progress_container.empty()
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

        # TAB DISPLAY
        papers_data = st.session_state.projects[st.session_state.active_project]["papers"]
        if papers_data:
            t1, t2, t3 = st.tabs(["🖼️ Individual Papers", "📊 Master Table", "🧠 Synthesis"])
            with t1:
                for idx, r in enumerate(reversed(papers_data)):
                    with st.container(border=True):
                        st.subheader(f"Ref {r.get('#')}: {r.get('Title')}")
                        st.write(f"🖊️ {r.get('Authors')} | 🗓️ {r.get('Year')}")
                        st.divider()
                        sections = [("📝 Summary", "Summary"), ("📖 Background", "Background"), ("⚙️ Methodology", "Methodology"), ("📍 Context", "Context"), ("💡 Findings", "Findings"), ("🛡️ Reliability", "Reliability")]
                        for label, key in sections:
                            st.markdown(f'<span class="section-title">{label}</span><span class="section-content">{r.get(key)}</span>', unsafe_allow_html=True)
            
            with t2:
                df = pd.DataFrame(papers_data)
                st.dataframe(df, use_container_width=True, hide_index=True)
                st.download_button("📊 Export CSV", df.to_csv(index=False).encode('utf-8-sig'), "review.csv")
                
            with t3:
                with st.container(border=True):
                    evidence = "".join([f"Paper {r.get('#')}: {r.get('Findings')}\n" for r in papers_data])
                    st.markdown("### Synthesis Overview")
                    if st.button("Generate Synthesis"):
                        with st.spinner("Writing..."):
                            prompt = "Synthesize these findings: " + evidence
                            st.write(llm.invoke([HumanMessage(content=prompt)]).content)

        # FOOTER
        st.divider()
        if st.button("🏠 Back to Library", use_container_width=True):
            st.session_state.active_project = None; st.rerun()
