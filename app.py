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
        if df is None or df.empty or 'Project' not in df.columns: 
            return {}
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
    except: return {}

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
        new_df = pd.DataFrame(flat_data)
        conn.update(data=new_df)

# 3. STYLING (Restoring original buttons and card layout)
st.markdown("""
<style>
[data-testid="stHeader"] { background-color: rgba(255, 255, 255, 0); }
:root { --buddy-green: #18A48C; --buddy-blue: #0000FF; }
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
    correct_password = "M1chaelL1tRev1ewTool2026!"
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
    api_key = "AIzaSyCs-N57rUlOl1J8LtwT54b6kLgYnAhmuJg"

    if 'projects' not in st.session_state:
        st.session_state.projects = load_full_library()
    if 'active_project' not in st.session_state:
        st.session_state.active_project = None 
    if 'renaming_project' not in st.session_state:
        st.session_state.renaming_project = None

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
                        with r_col1: new_name_val = st.text_input("Rename", value=proj_name, key=f"in_{proj_name}")
                        with r_col2: 
                            if st.button("✅", key=f"sav_{proj_name}"):
                                st.session_state.projects[new_name_val] = st.session_state.projects.pop(proj_name)
                                save_full_library(st.session_state.projects)
                                st.session_state.renaming_project = None
                                st.rerun()
                        with r_col3:
                            if st.button("❌", key=f"can_{proj_name}"):
                                st.session_state.renaming_project = None
                                st.rerun()
                    else:
                        col_name, col_spacer, col_edit, col_del, col_open = st.columns([6, 1.5, 0.5, 0.5, 0.5])
                        with col_name:
                            p_count = len(st.session_state.projects[proj_name]["papers"])
                            st.markdown(f"**📍 {proj_name}** ({p_count} Papers)")
                        with col_edit:
                            st.markdown('<div class="icon-btn">', unsafe_allow_html=True)
                            if st.button("🖊️", key=f"ed_{proj_name}"):
                                st.session_state.renaming_project = proj_name
                                st.rerun()
                            st.markdown('</div>', unsafe_allow_html=True)
                        with col_del:
                            st.markdown('<div class="icon-btn">', unsafe_allow_html=True)
                            if st.button("🗑️", key=f"dl_{proj_name}"):
                                del st.session_state.projects[proj_name]
                                save_full_library(st.session_state.projects)
                                st.rerun()
                            st.markdown('</div>', unsafe_allow_html=True)
                        with col_open:
                            st.markdown('<div class="icon-btn">', unsafe_allow_html=True)
                            if st.button("➡️", key=f"op_{proj_name}"):
                                st.session_state.active_project = proj_name
                                st.session_state.projects[proj_name]["last_accessed"] = time.time()
                                save_full_library(st.session_state.projects)
                                st.rerun()
                            st.markdown('</div>', unsafe_allow_html=True)
    else:
        # PROJECT VIEW
        st.markdown(f'<div class="fixed-header-bg"><div class="fixed-header-text"><h1>{st.session_state.active_project}</h1></div></div>', unsafe_allow_html=True)
        st.markdown('<div class="upload-pull-up">', unsafe_allow_html=True)
        llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", google_api_key=api_key, temperature=0.1)
        uploaded_files = st.file_uploader("Upload academic papers (PDF)", type="pdf", accept_multiple_files=True)
        run_review = st.button("🔬 Analyse paper", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

        if uploaded_files and run_review:
            for file in uploaded_files:
                reader = PdfReader(file)
                text = "".join([p.extract_text() for p in reader.pages if p.extract_text()]).strip()
                
                # THE SMARTER PHD PROMPT
                prompt = (
                    "Act as a Senior Academic Researcher and PhD Supervisor specializing in Systematic Literature Reviews. "
                    "Carefully analyze the text and extract for the following categories:\n\n"
                    "[TITLE]: The full academic title.\n[AUTHORS]: All primary authors.\n[YEAR]: Year of publication.\n"
                    "[REFERENCE]: Full Harvard-style citation.\n[SUMMARY]: Concise overview.\n"
                    "[BACKGROUND]: Gap and framework.\n[METHODOLOGY]: Design, N=, tools.\n[CONTEXT]: Location/population.\n"
                    "[FINDINGS]: Specific results.\n[RELIABILITY]: Critique limitations.\n\n"
                    "RULES: Output ONLY bracketed labels. No bolding or bullets. TEXT: " + text[:30000]
                )
                
                res = llm.invoke([HumanMessage(content=prompt)]).content
                res = re.sub(r'\*', '', res)
                def ext(label):
                    m = re.search(rf"\[{label}\]\s*:?\s*(.*?)(?=\s*\[|$)", res, re.DOTALL | re.IGNORECASE)
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
            save_full_library(st.session_state.projects)
            st.rerun()

        papers_data = st.session_state.projects[st.session_state.active_project]["papers"]
        if papers_data:
            t1, t2, t3 = st.tabs(["🖼️ Individual Papers", "📊 Master Table", "🧠 Synthesis"])
            with t1:
                for idx, r in enumerate(reversed(papers_data)):
                    real_idx = len(papers_data) - 1 - idx
                    with st.container(border=True):
                        st.subheader(f"Ref {r.get('#')}: {r.get('Title')}")
                        st.markdown(f'🖊️ Authors: {r.get("Authors")}<br>🗓️ Year: {r.get("Year")}<br>🔗 Full Citation: {r.get("Reference")}', unsafe_allow_html=True)
                        st.divider()
                        sections = [("📝 Summary", r.get("Summary")), ("📖 Background", r.get("Background")), ("⚙️ Methodology", r.get("Methodology")), ("📍 Context", r.get("Context")), ("💡 Findings", r.get("Findings")), ("🛡️ Reliability", r.get("Reliability"))]
                        for k, v in sections: st.markdown(f'<span class="section-title">{k}</span><span class="section-content">{v}</span>', unsafe_allow_html=True)
                        st.markdown('<div class="card-del-container">', unsafe_allow_html=True)
                        if st.button("🗑️ Delete Paper", key=f"del_p_{real_idx}"):
                            st.session_state.projects[st.session_state.active_project]["papers"].pop(real_idx)
                            save_full_library(st.session_state.projects); st.rerun()
                        st.markdown('</div>', unsafe_allow_html=True)
            with t2:
                st.dataframe(pd.DataFrame(papers_data), use_container_width=True, hide_index=True)
            with t3:
                evidence = "".join([f"Paper {r.get('#')}: {r.get('Findings')}\n" for r in papers_data])
                synth_res = llm.invoke([HumanMessage(content=f"Synthesize these findings into a high-level academic summary for a PhD review: {evidence}")]).content
                st.write(synth_res)

        st.columns([8, 1])[1].button("🏠 Library", on_click=lambda: setattr(st.session_state, 'active_project', None))
