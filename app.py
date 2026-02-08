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

# 2. DATABASE CONNECTION
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
            return True
        except Exception as e:
            st.error(f"⚠️ Storage Error: {e}")
            return False

# 3. STYLING
st.markdown("""
<style>
[data-testid="stHeader"] { background-color: rgba(255, 255, 255, 0); }
:root { --buddy-green: #18A48C; --buddy-blue: #0000FF; }
.section-title { font-weight: bold; color: #0000FF; margin-top: 1rem; display: block; text-transform: uppercase; font-size: 0.85rem; border-bottom: 0.06rem solid #eee; }
.section-content { display: block; margin-bottom: 10px; line-height: 1.6; color: #333; }
.fixed-header-bg { position: fixed; top: 0; left: 0; width: 100%; height: 4.5rem; background: white; border-bottom: 0.125rem solid #f0f2f6; z-index: 1000; padding-left: 3.75rem; display: flex; align-items: center; }
.fixed-header-text h1 { margin: 0; font-size: 2.2rem; color: #0000FF; }
.upload-pull-up { margin-top: -3.0rem !important; }
.synth-container { background-color: #f8f9fa; padding: 25px; border-radius: 12px; border-left: 8px solid #0000FF; margin-top: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
.icon-btn div[data-testid="stButton"] button { height: 38px !important; width: 38px !important; padding: 0 !important; border: none !important; background: transparent !important; }
</style>
""", unsafe_allow_html=True)

# 4. AUTHENTICATION
if "password_correct" not in st.session_state:
    st.markdown('<h1>📚 Literature Review Buddy</h1>', unsafe_allow_html=True)
    pwd = st.text_input("Enter password", type="password")
    if st.button("Unlock"):
        if pwd == "M1chaelL1tRev1ewTool2026!":
            st.session_state["password_correct"] = True
            st.rerun()
        else: st.error("🚫 Access Denied")
    st.stop()

# 5. MAIN LOGIC
api_key = "AIzaSyCs-N57rUlOl1J8LtwT54b6kLgYnAhmuJg"

if 'projects' not in st.session_state: st.session_state.projects = load_full_library()
if 'active_project' not in st.session_state: st.session_state.active_project = None 
if 'renaming_project' not in st.session_state: st.session_state.renaming_project = None
if 'processed_filenames' not in st.session_state: st.session_state.processed_filenames = set()

if st.session_state.active_project is None:
    # --- LIBRARY VIEW ---
    st.markdown('<div><h1 style="color:#0000FF;">🗂️ Project Library</h1><p style="color:#18A48C; font-weight: bold;">Permanent Cloud Storage Active.</p></div>', unsafe_allow_html=True)
    with st.container(border=True):
        c1, c2 = st.columns([4, 1])
        new_name = c1.text_input("New Project Name", placeholder="e.g. AI Ethics", label_visibility="collapsed")
        if c2.button("➕ Create Project", use_container_width=True):
            if new_name and new_name not in st.session_state.projects:
                st.session_state.projects[new_name] = {"papers": [], "last_accessed": time.time()}
                save_full_library(st.session_state.projects); st.session_state.active_project = new_name; st.rerun()

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
                        if st.button("❌", key=f"c_{proj_name}"): st.session_state.renaming_project = None; st.rerun()
                else:
                    col_name, col_spacer, col_edit, col_del, col_open = st.columns([6, 1.5, 0.5, 0.5, 0.5])
                    with col_name:
                        p_count = len(st.session_state.projects[proj_name]["papers"])
                        st.markdown(f"**📍 {proj_name}** ({p_count} Papers)")
                    for icon, key in [("🖊️", "ed"), ("🗑️", "dl"), ("➡️", "op")]:
                        with locals()[f"col_{'edit' if key=='ed' else 'del' if key=='dl' else 'open'}"]:
                            st.markdown('<div class="icon-btn">', unsafe_allow_html=True)
                            if st.button(icon, key=f"{key}_{proj_name}"):
                                if key == "ed": st.session_state.renaming_project = proj_name
                                elif key == "dl": 
                                    del st.session_state.projects[proj_name]
                                    save_full_library(st.session_state.projects)
                                else: 
                                    st.session_state.active_project = proj_name
                                    st.session_state.projects[proj_name]["last_accessed"] = time.time()
                                    save_full_library(st.session_state.projects)
                                st.rerun()
                            st.markdown('</div>', unsafe_allow_html=True)
else:
    # --- PROJECT VIEW ---
    st.markdown(f'<div class="fixed-header-bg"><div class="fixed-header-text"><h1>{st.session_state.active_project}</h1></div></div>', unsafe_allow_html=True)
    st.markdown('<div class="upload-pull-up">', unsafe_allow_html=True)
    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", google_api_key=api_key, temperature=0.1)
    uploaded_files = st.file_uploader("Upload academic papers (PDF)", type="pdf", accept_multiple_files=True)
    
    if st.button("🔬 Analyse paper", use_container_width=True):
        if uploaded_files:
            progress_container = st.empty()
            existing_titles = [p['Title'].lower() for p in st.session_state.projects[st.session_state.active_project]["papers"]]
            for file in uploaded_files:
                if file.name in st.session_state.processed_filenames: continue
                progress_container.info(f"📖 Analysing: {file.name}...")
                reader = PdfReader(file)
                text = "".join([p.extract_text() for p in reader.pages if p.extract_text()]).strip()
                prompt = "Act as Senior Academic Researcher. Extract: [TITLE], [AUTHORS], [YEAR], [REFERENCE], [SUMMARY], [BACKGROUND], [METHODOLOGY], [CONTEXT], [FINDINGS], [RELIABILITY]. RULES: Only labels, no bold/bullets. TEXT: " + text[:30000]
                res = llm.invoke([HumanMessage(content=prompt)]).content
                res = re.sub(r'\*', '', res)
                def ext(label):
                    m = re.search(rf"\[{label}\]\s*:?\s*(.*?)(?=\s*\[|$)", res, re.DOTALL | re.IGNORECASE)
                    return m.group(1).strip() if m else "Not explicitly stated."
                
                ext_title = ext("TITLE")
                if ext_title.lower() in existing_titles:
                    st.session_state.processed_filenames.add(file.name); continue

                new_paper = {"#": len(st.session_state.projects[st.session_state.active_project]["papers"]) + 1, "Title": ext_title, "Authors": ext("AUTHORS"), "Year": ext("YEAR"), "Reference": ext("REFERENCE"), "Summary": ext("SUMMARY"), "Background": ext("BACKGROUND"), "Methodology": ext("METHODOLOGY"), "Context": ext("CONTEXT"), "Findings": ext("FINDINGS"), "Reliability": ext("RELIABILITY")}
                st.session_state.projects[st.session_state.active_project]["papers"].append(new_paper)
                st.session_state.processed_filenames.add(file.name)
            progress_container.empty()
            save_full_library(st.session_state.projects); st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

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
                    sections = [("📝 Summary", "Summary"), ("📖 Background", "Background"), ("⚙️ Methodology", "Methodology"), ("📍 Context", "Context"), ("💡 Findings", "Findings"), ("🛡️ Reliability", "Reliability")]
                    for k, v in sections: st.markdown(f'<span class="section-title">{k}</span><span class="section-content">{r.get(v)}</span>', unsafe_allow_html=True)
                    if st.button("🗑️ Delete Paper", key=f"dp_{real_idx}"):
                        st.session_state.projects[st.session_state.active_project]["papers"].pop(real_idx)
                        save_full_library(st.session_state.projects); st.rerun()
        with t2:
            df = pd.DataFrame(papers_data)
            st.dataframe(df, use_container_width=True, hide_index=True)
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Export to CSV", data=csv, file_name=f"{st.session_state.active_project}_review.csv", mime='text/csv')
        with t3:
            st.markdown('<div class="synth-container">', unsafe_allow_html=True)
            st.markdown("### 🧠 Academic Synthesis")
            st.markdown("This section analyzes common themes, contradictions, and gaps across all uploaded papers in this project.")
            
            if st.button("🛠️ Generate/Refresh Synthesis"):
                with st.spinner("PhD Buddy is synthesizing themes..."):
                    # Pull findings from all papers
                    evidence_list = []
                    for p in papers_data:
                        ref_num = p.get('#', '?')
                        findings_text = p.get('Findings', 'No findings recorded.')
                        evidence_list.append(f"Paper {ref_num}: {findings_text}")
                    
                    full_evidence = "\n\n".join(evidence_list)
                    
                    synthesis_prompt = (
                        "You are an expert PhD Supervisor. Provide a critical synthesis of the following research findings. "
                        "Identify: 1) Common themes across papers. 2) Significant contradictions or debates. "
                        "3) Gaps in the current research. 4) A concluding summary of the project's overall contribution. "
                        "Format with clear headings and a professional academic tone.\n\n"
                        f"FINDINGS DATA:\n{full_evidence}"
                    )
                    
                    try:
                        synth_res = llm.invoke([HumanMessage(content=synthesis_prompt)]).content
                        st.session_state[f"synth_{st.session_state.active_project}"] = synth_res
                    except Exception as e:
                        st.error(f"AI Synthesis failed: {e}")

            # Display saved synthesis if it exists
            stored_synth = st.session_state.get(f"synth_{st.session_state.active_project}")
            if stored_synth:
                st.markdown("---")
                st.markdown(stored_synth)
            st.markdown('</div>', unsafe_allow_html=True)

    # RIGHT ALIGNED ACTIONS
    st.divider()
    b_col1, b_col2, b_col3 = st.columns([8, 1, 1])
    with b_col2:
        if st.button("💾 Save", use_container_width=True):
            if save_full_library(st.session_state.projects): st.success("Saved!")
    with b_col3:
        if st.button("🏠 Library", use_container_width=True):
            st.session_state.processed_filenames = set(); st.session_state.active_project = None; st.rerun()
