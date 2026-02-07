import streamlit as st
import pandas as pd
from pypdf import PdfReader
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
import re

st.set_page_config(page_title="PhD Literature Reviewer", layout="wide")

# --- CSS: Full Width & Clean UI ---
st.markdown("""
    <style>
    [data-testid="stHeader"] { background-color: rgba(255, 255, 255, 0); }
    .sticky-wrapper {
        position: fixed; top: 0; left: 0; width: 100%;
        background-color: white; z-index: 1000;
        padding: 40px 50px 10px 50px; border-bottom: 2px solid #f0f2f6;
    }
    .main-content { margin-top: 90px; }
    [data-testid="stFileUploaderContainer"] section { padding: 0px !important; width: 100% !important; }
    div.stButton > button:first-child {
        width: 100% !important; color: #28a745 !important;
        border: 2px solid #28a745 !important; font-weight: bold !important;
        margin-top: 15px; background-color: transparent !important;
    }
    .section-title { font-weight: bold; color: #1f77b4; margin-top: 25px; display: block; text-transform: uppercase; font-size: 0.85rem; border-bottom: 1px solid #eee; }
    .section-content { display: block; margin-bottom: 20px; line-height: 1.7; color: #333; }
    </style>
    """, unsafe_allow_html=True)

# --- STATE ---
if 'master_data' not in st.session_state: st.session_state.master_data = [] 
if 'processed_filenames' not in st.session_state: st.session_state.processed_filenames = set() 

st.markdown('<div class="sticky-wrapper"><h1 style="margin:0;">🎓 PhD Research Extractor</h1><p style="color:gray; margin-bottom:10px;">PhD Reviewer Mode | Gemini 2.0 Flash</p></div>', unsafe_allow_html=True)

with st.container():
    st.markdown('<div class="main-content">', unsafe_allow_html=True)
    
    # Use Secrets if available, else empty string
    api_key = st.secrets.get("GEMINI_API_KEY", "")
    if not api_key:
        api_key = st.text_input("Gemini API Key", type="password")
    
    llm = None
    if api_key:
        llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", google_api_key=api_key, temperature=0.1)

    st.divider()
    uploaded_files = st.file_uploader("Upload academic papers", type="pdf", accept_multiple_files=True)
    run_review = st.button("🔬 Execute Full-Text Review", use_container_width=True)

    if uploaded_files and llm and run_review:
        progress_text = st.empty()
        for file in uploaded_files:
            if file.name in st.session_state.processed_filenames: continue
            progress_text.text(f"Analyzing: {file.name}...")
            try:
                reader = PdfReader(file) 
                full_text = "".join([page.extract_text() for page in reader.pages if page.extract_text()]).strip()
                
                if not full_text:
                    st.warning(f"Could not read text from {file.name}. Skipping.")
                    continue

                prompt = f"""
                You are a senior PhD academic reviewer. Extract data with high precision.
                DO NOT use bullet points. Use cohesive paragraphs.
                
                Markers to use: [TITLE], [AUTHORS], [YEAR], [REFERENCE], [SUMMARY], [BACKGROUND], [METHODOLOGY], [CONTEXT], [FINDINGS], [RELIABILITY].
                
                TEXT TO ANALYZE:
                {full_text}
                """
                
                # Using a single HumanMessage is safer for Gemini than mixing System/Human in some cloud environments
                response = llm.invoke([HumanMessage(content=prompt)])
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
            except Exception as e: st.error(f"Error on {file.name}: {e}")
        progress_text.empty()

    if st.session_state.master_data:
        t1, t2, t3 = st.tabs(["🖼️ Card Gallery", "📊 Master Table", "🧠 Synthesis"])
        with t1:
            for r in reversed(st.session_state.master_data):
                with st.container(border=True):
                    cr, ct = st.columns([1, 12]); cr.metric("Ref", r['#']); ct.subheader(r['Title'])
                    st.divider()
                    sections = [("Summary", r["Summary"]), ("📖 Background", r["Background"]), ("⚙️ Methodology", r["Methodology"]), ("📍 Context", r["Context"]), ("💡 Findings", r["Findings"]), ("🛡️ Reliability", r["Reliability"])]
                    for k, v in sections:
                        st.markdown(f'<span class="section-title">{k}</span><span class="section-content">{v}</span>', unsafe_allow_html=True)
        with t2:
            st.dataframe(pd.DataFrame(st.session_state.master_data), use_container_width=True, hide_index=True)
        with t3:
            if llm:
                # Group findings and ensure they aren't empty
                findings_list = [f"Paper {r['#']} ({r['Title']}): {r['Findings']}" for r in st.session_state.master_data if r['Findings'] != "Data not found"]
                if findings_list:
                    with st.spinner("Synthesizing..."):
                        synth_query = "Perform a PhD-level meta-synthesis of these research findings:\n\n" + "\n\n".join(findings_list)
                        synth_res = llm.invoke([HumanMessage(content=synth_query)])
                        st.markdown(synth_res.content)
                else:
                    st.info("No valid findings found to synthesize yet.")

    st.markdown('</div>', unsafe_allow_html=True)
