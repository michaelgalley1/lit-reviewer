import streamlit as st
import pandas as pd
from pypdf import PdfReader
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
import re
import time

# 1. PAGE CONFIGURATION
st.set_page_config(page_title="PhD Research Extractor", layout="wide")

# 2. STYLING (CSS)
st.markdown("""
    <style>
    [data-testid="stHeader"] { background-color: rgba(255, 255, 255, 0); }
    .sticky-wrapper {
        position: fixed; top: 0; left: 0; width: 100%;
        background-color: white; z-index: 1000;
        padding: 10px 50px 0px 50px; border-bottom: 2px solid #f0f2f6;
    }
    .main-content { margin-top: -75px; }
    .block-container { padding-top: 0rem !important; }
    [data-testid="stFileUploader"] { padding-top: 0px !important; }
    div.stButton > button:first-child {
        width: 100% !important; color: #28a745 !important;
        border: 2px solid #28a745 !important; font-weight: bold !important;
        background-color: transparent !important;
    }
    .section-title { font-weight: bold; color: #1f77b4; margin-top: 15px; display: block; text-transform: uppercase; font-size: 0.85rem; border-bottom: 1px solid #eee; }
    .section-content { display: block; margin-bottom: 10px; line-height: 1.6; color: #333; }
    </style>
    """, unsafe_allow_html=True)

# 3. AUTHENTICATION
def check_password():
    correct_password = st.secrets.get("APP_PASSWORD")
    if "password_correct" not in st.session_state:
        st.markdown("### 🔒 Research Gateway")
        pwd = st.text_input("Enter Access Password", type="password")
        if st.button("Unlock Tool"):
            if pwd == correct_password:
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("🚫 Access Denied")
        return False
    return True

# 4. MAIN APPLICATION
if check_password():
    api_key = st.secrets.get("GEMINI_API_KEY")

    if 'master_data' not in st.session_state: st.session_state.master_data = [] 
    if 'processed_filenames' not in st.session_state: st.session_state.processed_filenames = set() 

    st.markdown('<div class="sticky-wrapper"><h1 style="margin:0; font-size: 1.8rem;">🎓 PhD Research Extractor</h1><p style="color:gray; margin-bottom:5px;">Advanced Academic Review Mode</p></div>', unsafe_allow_html=True)

    with st.container():
        st.write("##") 
        st.markdown('<div class="main-content">', unsafe_allow_html=True)
        
        llm = None
        if api_key:
            llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", google_api_key=api_key, temperature=0.1)

        uploaded_files = st.file_uploader("Upload academic papers (PDF)", type="pdf", accept_multiple_files=True)
        run_review = st.button("🔬 Execute High-Level Synthesis", use_container_width=True)

        if uploaded_files and llm and run_review:
            progress_text = st.empty()
            for i, file in enumerate(uploaded_files):
                if file.name in st.session_state.processed_filenames: continue
                
                if i > 0:
                    for s in range(5, 0, -1):
                        progress_text.text(f"⏳ API Cool-down... {s}s")
                        time.sleep(1)

                progress_text.text(f"📖 Deep-Reading: {file.name}...")
                try:
                    reader = PdfReader(file) 
                    text = "".join([p.extract_text() for p in reader.pages if p.extract_text()]).strip()
                    
                    # ENHANCED PHD PROMPT
                    prompt = f"""
                    You are an expert senior academic researcher and peer reviewer. 
                    Analyze the provided text with extreme rigor, focusing on theoretical contributions, methodological nuances, and statistical validity.

                    REQUIRED FORMAT:
                    Use ONLY these exact labels: [TITLE], [AUTHORS], [YEAR], [REFERENCE], [SUMMARY], [BACKGROUND], [METHODOLOGY], [CONTEXT], [FINDINGS], [RELIABILITY].

                    INSTRUCTIONS FOR CONTENT QUALITY:
                    - [SUMMARY]: Provide a dense 3-4 sentence overview of the core thesis and contribution.
                    - [METHODOLOGY]: Detail the specific research design, sample characteristics (N=), variables, and statistical/qualitative tools used.
                    - [FINDINGS]: Do not just list results; explain the implications of the primary data and any p-values or effect sizes mentioned.
                    - [RELIABILITY]: Critically assess limitations, potential biases, or gaps in the study's logic.
                    - CRITICAL: Do NOT use any bolding or asterisks (**). Use plain text only.

                    Text to analyze: {text[:40000]}
                    """
                    
                    res = llm.invoke([HumanMessage(content=prompt)]).content
                    res = re.sub(r'\*', '', res) # Nuclear option for asterisks

                    def ext(label, next_l=None):
                        p = rf"\[{label}\]:?\s*(.*?)(?=\s*\[{next_l}\]|$)" if next_l else rf"\[{label}\]:?\s*(.*)"
                        m = re.search(p, res, re.DOTALL | re.IGNORECASE)
                        return m.group(1).strip() if m else "Depth insufficient in text"

                    st.session_state.master_data.append({
                        "#": len(st.session_state.master_data) + 1,
                        "Title": ext("TITLE", "AUTHORS"),
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
                        sec = [("Summary", r["Summary"]), ("📖 Background", r["Background"]), ("⚙️ Methodology", r["Methodology"]), ("📍 Context", r["Context"]), ("💡 Findings", r["Findings"]), ("🛡️ Reliability", r["Reliability"])]
                        for k, v in sec:
                            st.markdown(f'<span class="section-title">{k}</span><span class="section-content">{v}</span>', unsafe_allow_html=True)
            with t2:
                st.dataframe(pd.DataFrame(st.session_state.master_data), use_container_width=True, hide_index=True)
            with t3:
                if llm:
                    f_list = [f"Paper {r['#']} ({r['Title']}): {r['Findings']}" for r in st.session_state.master_data]
                    with st.spinner("Generating Meta-Synthesis..."):
                        synth_prompt = f"Perform a high-level thematic meta-analysis and synthesis of these findings. Identify cross-study patterns and contradictions in plain text:\n\n" + "\n\n".join(f_list)
                        st.markdown(llm.invoke([HumanMessage(content=synth_prompt)]).content)
    st.markdown('</div>', unsafe_allow_html=True)
