import streamlit as st
import pandas as pd
from pypdf import PdfReader
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
import re
import time

# 1. PAGE CONFIGURATION
st.set_page_config(page_title="Literature Review Buddy", page_icon="📚", layout="wide")

# 2. STYLING (Branding #18A48C preserved)
st.markdown("""
<style>
[data-testid="stHeader"] { background-color: rgba(255, 255, 255, 0); }
:root { --buddy-green: #18A48C; --buddy-blue: #0000FF; }
[data-testid="block-container"] { padding-top: 0rem !important; }

/* Global Input Borders */
div[data-baseweb="input"], div[data-baseweb="textarea"] { border: 1px solid var(--buddy-green) !important; }
button:hover { background-color: var(--buddy-green) !important; border-color: var(--buddy-green) !important; color: white !important; }

/* Tab Styling - Green underline, No red underline */
button[data-baseweb="tab"] { background-color: transparent !important; }
button[data-baseweb="tab"]:hover { background-color: transparent !important; color: var(--buddy-green) !important; }
button[data-baseweb="tab"][aria-selected="true"] { color: var(--buddy-green) !important; border-bottom: 2px solid var(--buddy-green) !important; }
div[data-baseweb="tab-highlight"] { background-color: transparent !important; visibility: hidden !important; }

.synth-card { min-height: 280px; border: 1px solid #e6e9ef; border-radius: 0.5rem; padding: 1.2rem; background-color: white; }
.section-title { font-weight: bold; color: var(--buddy-blue); margin-top: 1rem; display: block; text-transform: uppercase; font-size: 0.85rem; border-bottom: 0.06rem solid #eee; }
.section-content { display: block; margin-bottom: 10px; line-height: 1.6; color: #333; }
.fixed-header-bg { position: fixed; top: 0; left: 0; width: 100%; height: 4.5rem; background: white; border-bottom: 0.125rem solid #f0f2f6; z-index: 1000; padding-left: 3.75rem; display: flex; align-items: center; }
.fixed-header-text h1 { margin: 0; font-size: 2.2rem; color: var(--buddy-blue); }
.upload-pull-up { margin-top: -3.0rem !important; }
.icon-btn div[data-testid="stButton"] button { height: 38px !important; width: 38px !important; padding: 0 !important; border: none !important; background: transparent !important; }
</style>
""", unsafe_allow_html=True)

# 3. AUTHENTICATION
if "password_correct" not in st.session_state:
    st.markdown('<h1>📚 Literature Review Buddy</h1>', unsafe_allow_html=True)
    pwd = st.text_input("Enter password", type="password")
    if st.button("Unlock"):
        if pwd == st.secrets["APP_PASSWORD"]:
            st.session_state["password_correct"] = True
            st.rerun()
        else: st.error("🚫 Access Denied")
    st.stop()

# 4. INITIALIZE LOCAL STORAGE
if 'projects' not in st.session_state: st.session_state.projects = {}
if 'active_project' not in st.session_state: st.session_state.active_project = None 
if 'processed_filenames' not in st.session_state: st.session_state.processed_filenames = set()

api_key = st.secrets["GEMINI_API_KEY"]
llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", google_api_key=api_key, temperature=0.1)

# 5. MAIN LOGIC
if st.session_state.active_project is None:
    # --- LIBRARY VIEW ---
    st.markdown('<div><h1 style="color:#0000FF;">🗂️ Project Library</h1><p style="color:#18A48C;">Local Session Storage Enabled.</p></div>', unsafe_allow_html=True)
    with st.container(border=True):
        c1, c2 = st.columns([4, 1])
        new_name = c1.text_input("New Project Name", placeholder="e.g. AI Ethics", key="new_proj_input")
        if c2.button("➕ Create Project", use_container_width=True):
            if new_name and new_name not in st.session_state.projects:
                st.session_state.projects[new_name] = {"papers": [], "last_accessed": time.time()}
                st.session_state.active_project = new_name
                st.rerun()

    for proj_name in sorted(st.session_state.projects.keys(), key=lambda k: st.session_state.projects[k]['last_accessed'], reverse=True):
        with st.container(border=True):
            col_name, col_spacer, col_edit, col_del, col_open = st.columns([6, 1.5, 0.5, 0.5, 0.5])
            with col_name:
                p_count = len(st.session_state.projects[proj_name]["papers"])
                st.markdown(f"**📍 {proj_name}** ({p_count} Papers)")
            with col_del:
                if st.button("🗑️", key=f"dl_{proj_name}"):
                    del st.session_state.projects[proj_name]; st.rerun()
            with col_open:
                if st.button("➡️", key=f"op_{proj_name}"):
                    st.session_state.active_project = proj_name; st.rerun()
else:
    # --- PROJECT VIEW ---
    st.markdown(f'<div class="fixed-header-bg"><div class="fixed-header-text"><h1>{st.session_state.active_project}</h1></div></div>', unsafe_allow_html=True)
    st.markdown('<div class="upload-pull-up">', unsafe_allow_html=True)
    uploaded_files = st.file_uploader("Upload PDFs", type="pdf", accept_multiple_files=True)
    
    if st.button("🔬 Analyse paper", use_container_width=True):
        if uploaded_files:
            progress_container = st.empty()
            for file in uploaded_files:
                if file.name in st.session_state.processed_filenames: continue
                progress_container.info(f"📖 Reading: {file.name}...")
                reader = PdfReader(file)
                text = "".join([p.extract_text() for p in reader.pages[:15] if p.extract_text()]).strip()
                
                prompt = "Act as Senior PhD Supervisor. Analysis: [TITLE], [AUTHORS], [YEAR], [REFERENCE], [SUMMARY], [BACKGROUND], [METHODOLOGY], [CONTEXT], [FINDINGS], [RELIABILITY]. NO BOLD/STARS. TEXT: " + text[:35000]
                res = llm.invoke([HumanMessage(content=prompt)]).content
                
                def fuzzy_ext(label):
                    clean_res = re.sub(r'\*', '', res)
                    m = re.search(rf"\[?{label}\]?\s*:?\s*(.*?)(?=\s*\[|$)", clean_res, re.DOTALL | re.IGNORECASE)
                    return m.group(1).strip() if m else "Not found."

                st.session_state.projects[st.session_state.active_project]["papers"].append({
                    "#": len(st.session_state.projects[st.session_state.active_project]["papers"]) + 1,
                    "Title": fuzzy_ext("TITLE"), "Authors": fuzzy_ext("AUTHORS"), "Year": fuzzy_ext("YEAR"), 
                    "Reference": fuzzy_ext("REFERENCE"), "Summary": fuzzy_ext("SUMMARY"), 
                    "Background": fuzzy_ext("BACKGROUND"), "Methodology": fuzzy_ext("METHODOLOGY"), 
                    "Context": fuzzy_ext("CONTEXT"), "Findings": fuzzy_ext("FINDINGS"), 
                    "Reliability": fuzzy_ext("RELIABILITY")
                })
                st.session_state.processed_filenames.add(file.name)
            progress_container.empty(); st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    papers_data = st.session_state.projects[st.session_state.active_project]["papers"]
    if papers_data:
        t1, t2, t3 = st.tabs(["🖼️ Individual Papers", "📊 Master Table", "🧠 Synthesis"])
        with t1:
            for idx, r in enumerate(reversed(papers_data)):
                with st.container(border=True):
                    st.subheader(f"Ref {r.get('#')}: {r.get('Title')}")
                    st.markdown(f'🖊️ Authors: {r.get("Authors")} | 🗓️ Year: {r.get("Year")}<br>🔗 Citation: {r.get("Reference")}', unsafe_allow_html=True)
                    st.divider()
                    for k, v in [("📝 Summary", "Summary"), ("📖 Background", "Background"), ("⚙️ Methodology", "Methodology"), ("📍 Context", "Context"), ("💡 Findings", "Findings"), ("🛡️ Reliability", "Reliability")]:
                        st.markdown(f'<span class="section-title">{k}</span><span class="section-content">{r.get(v)}</span>', unsafe_allow_html=True)
        with t2:
            df = pd.DataFrame(papers_data)
            st.dataframe(df, use_container_width=True, hide_index=True)
            st.download_button("📥 Export CSV", data=df.to_csv(index=False).encode('utf-8'), file_name="review.csv")
        with t3:
            synth_data = st.session_state.get(f"synth_{st.session_state.active_project}", {})
            if synth_data:
                c1, c2 = st.columns(2)
                with c1: st.markdown(f'<div class="synth-card">📋 <b>Overview</b><br><br>{synth_data.get("overview")}</div>', unsafe_allow_html=True)
                with c2: st.markdown(f'<div class="synth-card">🤝 <b>Overlaps</b><br><br>{synth_data.get("overlaps")}</div>', unsafe_allow_html=True)
                st.markdown("<br>", unsafe_allow_html=True)
                c3, c4 = st.columns(2)
                with c3: st.markdown(f'<div class="synth-card">⚔️ <b>Contradictions</b><br><br>{synth_data.get("contradictions")}</div>', unsafe_allow_html=True)
                with c4: st.markdown(f'<div class="synth-card">🚀 <b>Future Research</b><br><br>{synth_data.get("future")}</div>', unsafe_allow_html=True)
            
            if st.button("🔄 Try Again"):
                evidence = "".join([f"Paper {r.get('#')}: {r.get('Findings')}\n" for r in papers_data])
                prompt = "PhD Synthesis: [OVERVIEW], [OVERLAPS], [CONTRADICTIONS], [FUTURE]. DATA: " + evidence
                res = llm.invoke([HumanMessage(content=prompt)]).content
                def get_p(lbl):
                    m = re.search(rf"\[{lbl}\]\s*:?\s*(.*?)(?=\s*\[|$)", res, re.DOTALL | re.IGNORECASE)
                    return m.group(1).strip() if m else "..."
                st.session_state[f"synth_{st.session_state.active_project}"] = {"overview": get_p("OVERVIEW"), "overlaps": get_p("OVERLAPS"), "contradictions": get_p("CONTRADICTIONS"), "future": get_p("FUTURE")}
                st.rerun()

    st.columns([9, 1])[1].button("🏠 Library", on_click=lambda: setattr(st.session_state, 'active_project', None))
