import streamlit as st
import pandas as pd
from pypdf import PdfReader
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema import HumanMessage, SystemMessage
import re

st.set_page_config(page_title="PhD Literature Reviewer", layout="wide")

# --- CUSTOM CSS ---
st.markdown("""
    <style>
    [data-testid="stHeader"] { background-color: rgba(255, 255, 255, 0); }
    .sticky-wrapper {
        position: fixed; top: 0; left: 0; width: 100%;
        background-color: white; z-index: 1000;
        padding: 40px 50px 10px 50px; border-bottom: 2px solid #f0f2f6;
    }
    .main-content { margin-top: 90px; }
    
    /* Full Width Uploader */
    [data-testid="stFileUploaderContainer"] section { padding: 0px !important; width: 100% !important; }
    [data-testid="stFileUploaderContainer"] section > div { height: 65px !important; min-height: 65px !important; }

    /* Green Execute Button */
    div.stButton > button:first-child {
        width: 100% !important; color: #28a745 !important;
        border: 2px solid #28a745 !important; font-weight: bold !important;
        margin-top: 15px; background-color: transparent !important;
        transition: all 0.3s ease-in-out !important;
    }
    div.stButton > button:first-child p { color: #28a745 !important; }
    div.stButton > button:first-child:hover {
        background-color: #F6FFF8 !important;
        box-shadow: 0px 0px 12px rgba(40, 167, 69, 0.2) !important;
        transform: translateY(-2px);
    }

    .meta-container { display: flex; flex-direction: column; gap: 6px; margin-top: 10px; }
    .meta-item { display: flex; align-items: flex-start; font-size: 0.95rem; }
    .meta-label { font-weight: bold; color: #444; min-width: 140px; }
    .meta-value { color: #111; flex: 1; }
    .section-title { font-weight: bold; color: #1f77b4; margin-top: 25px; margin-bottom: 5px; display: block; text-transform: uppercase; font-size: 0.85rem; border-bottom: 1px solid #eee; padding-bottom: 3px; }
    .section-content { display: block; margin-bottom: 20px; line-height: 1.7; color: #333; }
    </style>
    """, unsafe_allow_html=True)

# --- STATE ---
if 'master_data' not in st.session_state: st.session_state.master_data = [] 
if 'processed_filenames' not in st.session_state: st.session_state.processed_filenames = set() 

st.markdown('<div class="sticky-wrapper"><h1 style="margin:0;">🎓 PhD-Level Research Extractor</h1><p style="color:gray; margin-bottom:10px;">Engine: Gemini 2.0 Flash | PhD Reviewer Mode</p></div>', unsafe_allow_html=True)

with st.container():
    st.markdown('<div class="main-content">', unsafe_allow_html=True)
    api_key = st.text_input("Gemini API Key", value="AIzaSyBp79CK2QBOLM_Baka2eDles9jElktUqpI", type="password")
    
    llm = None
    if api_key:
        llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", google_api_key=api_key, temperature=0.1)

    st.divider()
    uploaded_files = st.file_uploader("Upload academic paper here", type="pdf", accept_multiple_files=True)
    run_review = st.button("🔬 Execute Full-Text Review", use_container_width=True)

    if uploaded_files and llm and run_review:
        progress_text = st.empty()
        for file in uploaded_files:
            if file.name in st.session_state.processed_filenames: continue
            progress_text.text(f"Deep-reading: {file.name}...")
            try:
                reader = PdfReader(file) 
                full_text = "".join([page.extract_text() for page in reader.pages if page.extract_text()])
                
                system_instruction = """
                You are a senior PhD academic reviewer. Provide a dense, highly detailed analysis.
                DO NOT use bullet points or lists. Use sophisticated academic prose in cohesive paragraphs.
                
                You MUST use these exact markers for each section:
                [TITLE]: Full formal title.
                [AUTHORS]: All listed authors.
                [YEAR]: Publication year.
                [REFERENCE]: Full citation and DOI.
                [SUMMARY]: One-sentence executive focus.
                [BACKGROUND]: Theory, motivation, and the specific literature gap.
                [METHODOLOGY]: Research design, variables, and technical analysis used.
                [CONTEXT]: Setting, demographics, and geography.
                [FINDINGS]: Deep dive into results and statistical/qualitative data.
                [RELIABILITY]: Critical appraisal of limitations and data robustness.
                """
                
                response = llm.invoke([SystemMessage(content=system_instruction), HumanMessage(content=full_text)])
                res_text = response.content

                def extract(label, next_label=None):
                    pattern = rf"\[{label}\]:?\s*(.*?)(?=\s*\[{next_label}\]|$)" if next_label else rf"\[{label}\]:?\s*(.*)"
                    match = re.search(pattern, res_text, re.DOTALL | re.IGNORECASE)
                    return match.group(1).strip() if match else "Data not found"

                st.session_state.master_data.append({
                    "#": len(st.session_state.master_data) + 1,
                    "Title": extract("TITLE", "AUTHORS"),
                    "Authors": extract("AUTHORS", "YEAR"),
                    "Year": extract("YEAR", "REFERENCE"),
                    "Reference": extract("REFERENCE", "SUMMARY"),
                    "Summary": extract("SUMMARY", "BACKGROUND"),
                    "Background": extract("BACKGROUND", "METHODOLOGY"),
                    "Methodology": extract("METHODOLOGY", "CONTEXT"),
                    "Context": extract("CONTEXT", "FINDINGS"),
                    "Findings": extract("FINDINGS", "RELIABILITY"),
                    "Reliability": extract("RELIABILITY")
                })
                st.session_state.processed_filenames.add(file.name)
            except Exception as e: st.error(f"Error analyzing {file.name}: {e}")
        progress_text.empty()

    if st.session_state.master_data:
        t1, t2, t3 = st.tabs(["🖼️ Card Gallery", "📊 Master Table", "🧠 Synthesis"])
        with t1:
            for r in reversed(st.session_state.master_data):
                with st.container(border=True):
                    cr, ct = st.columns([1, 12]); cr.metric("Ref", r['#']); ct.subheader(r['Title'])
                    st.markdown(f'<div class="meta-container"><div class="meta-item"><span class="meta-label">👤 AUTHORS:</span><span class="meta-value">{r["Authors"]}</span></div><div class="meta-item"><span class="meta-label">📅 YEAR:</span><span class="meta-value">{r["Year"]}</span></div><div class="meta-item"><span class="meta-label">🔗 REFERENCE:</span><span class="meta-value">{r["Reference"]}</span></div></div>', unsafe_allow_html=True)
                    st.divider()
                    sections = [("Summary", r["Summary"]), ("📖 Background", r["Background"]), ("⚙️ Methodology", r["Methodology"]), ("📍 Context", r["Context"]), ("💡 Findings", r["Findings"]), ("🛡️ Reliability", r["Reliability"])]
                    for k, v in sections:
                        st.markdown(f'<span class="section-title">{k}</span><span class="section-content">{v}</span>', unsafe_allow_html=True)
        
        with t2: 
            # FIX: Convert to DataFrame and hide the default 0-based index
            df = pd.DataFrame(st.session_state.master_data)
            st.dataframe(df, use_container_width=True, hide_index=True)
            
        with t3:
            if llm:
                with st.spinner("Synthesizing..."):
                    txt = "\n".join([f"Paper {r['#']}: {r['Findings']}" for r in st.session_state.master_data])
                    st.markdown(llm.invoke([HumanMessage(content=f"Synthesize these findings:\n{txt}")]).content)
    st.markdown('</div>', unsafe_allow_html=True)
