import streamlit as st
import pandas as pd
from pypdf import PdfReader
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
import re
import time

# 1. PAGE CONFIGURATION
st.set_page_config(page_title="Literature Review Buddy", page_icon="📚", layout="wide")

# 2. STYLING (CSS)
st.markdown("""
    <style>
    [data-testid="stHeader"] { background-color: rgba(255, 255, 255, 0); }
    
    /* Global Green Branding: #18A48C */
    :root {
        --buddy-green: #18A48C;
        --buddy-blue: #0000FF;
    }

    /* Remove red outline/flash on input focus */
    input:focus {
        outline: none !important;
        box-shadow: 0 0 0 2px rgba(24, 164, 140, 0.2) !important;
        border-color: var(--buddy-green) !important;
    }

    .sticky-wrapper {
        position: fixed; top: 0; left: 0; width: 100%;
        background-color: white; z-index: 1000;
        padding: 10px 50px 0px 50px;
        border-bottom: 2px solid #f0f2f6;
    }
    
    .main-content { 
        margin-top: -75px; 
    }

    .block-container {
        padding-top: 0rem !important;
    }

    [data-testid="stFileUploader"] { padding-top: 0px !important; }
    
    /* Primary Button Styling */
    div.stButton > button:first-child {
        width: 100% !important; 
        color: var(--buddy-green) !important;
        border: 2px solid var(--buddy-green) !important; 
        font-weight: bold !important;
        background-color: transparent !important;
    }
    
    div.stButton > button:hover {
        background-color: var(--buddy-green) !important;
        color: white !important;
    }

    .section-title { font-weight: bold; color: #1f77b4; margin-top: 15px; display: block; text-transform: uppercase; font-size: 0.85rem; border-bottom: 1px solid #eee; }
    .section-content { display: block; margin-bottom: 10px; line-height: 1.6; color: #333; }
    </style>
    """, unsafe_allow_html=True)

# 3. AUTHENTICATION
def check_password():
    correct_password = st.secrets.get("APP_PASSWORD")
    if "password_correct" not in st.session_state:
        # Title color changed to #0000FF Blue
        st.markdown(f"<h3 style='color:#0000FF;'>📚 Buddy Access Gateway</h3>", unsafe_allow_html=True)
        
        # Wording updated for the password prompt
        pwd = st.text_input("Enter password to unlock Literature Review Buddy", type="password")
        
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

    # STICKY HEADER
    st.markdown(f'''
        <div class="sticky-wrapper">
            <h1 style="margin:0; font-size: 1.8rem;">📚 Literature Review Buddy</h1>
            <p style="color:#18A48C; margin-bottom:5px; font-weight: bold;">Your PhD-Level Research Assistant</p>
        </div>
    ''', unsafe_allow_html=True)

    with st.container():
        st.write("##") 
        st.markdown('<div class="main-content">', unsafe_allow_html=True)
        
        llm = None
        if api_key:
            llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", google_api_key=api_key, temperature=0.1)

        uploaded_files = st.file_uploader("Upload academic papers (PDF)", type="pdf", accept_multiple_files=True)
        run_review = st.button("🔬 Analyse paper", use_container_width=True)

        if uploaded_files and llm and run_review:
            progress_text = st.empty()
            for i, file in enumerate(uploaded_files):
                if file.name in st.session_state.processed_filenames: continue
                
                if i > 0:
                    for s in range(5, 0, -1):
                        progress_text.text(f"⏳ API Cool-down... {s}s")
                        time.sleep(1)

                progress_text.text(f"📖 Buddy is reading the full text: {file.name}...")
                try:
                    reader = PdfReader(file) 
                    text = "".join([p.extract_text() for p in reader.pages if p.extract_text()]).strip()
                    
                    prompt = f"""
                    You are a senior academic researcher. Analyze the ATTACHED FULL TEXT with extreme rigor.
                    Provide a deep methodological and theoretical critique.

                    REQUIRED FORMAT:
                    Use ONLY these exact labels: [TITLE], [AUTHORS], [YEAR], [REFERENCE], [SUMMARY], [BACKGROUND], [METHODOLOGY], [CONTEXT], [FINDINGS], [RELIABILITY].

                    EXPECTATIONS:
                    - [METHODOLOGY]: Specific design, N-values, sampling, and statistical tests.
                    - [FINDINGS]: Interpretation of significance, effect sizes, or p-values.
                    - [RELIABILITY]: Evaluation of validity and specific limitations.
                    - CRITICAL: Plain text only. No asterisks (**), no bolding.

                    FULL TEXT: {text}
                    """
                    
                    res = llm.invoke([HumanMessage(content=prompt)]).content
                    res = re.sub(r'\*', '', res) 

                    def ext(label, next_l=None):
                        p = rf"\[{label}\]:?\s*(.*?)(?=\s*\[{next_l}\]|$)" if next_l else rf"\[{label}\]:?\s*(.*)"
                        m = re.search(p, res, re.DOTALL | re.IGNORECASE)
                        return m.group(1).strip() if m else "Depth insufficient in source text"

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
                    with st.spinner("Buddy is generating your synthesis..."):
                        synth_prompt = f"""
                        Perform a PhD-level meta-synthesis of these findings. 
                        Use these EXACT labels: [OVERVIEW], [PATTERNS], [CONTRADICTIONS], [FUTURE_DIRECTIONS].
                        Plain text only. No asterisks (**).
                        
                        Data: {" / ".join(f_list)}
                        """
                        raw_synth = llm.invoke([HumanMessage(content=synth_prompt)]).content
                        clean_synth = re.sub(r'\*', '', raw_synth)

                        def get_synth(label, next_l=None):
                            p = rf"\[{label}\]:?\s*(.*?)(?=\s*\[{next_l}\]|$)" if next_l else rf"\[{label}\]:?\s*(.*)"
                            m = re.search(p, clean_synth, re.DOTALL | re.IGNORECASE)
                            return m.group(1).strip() if m else "Synthesis detail not found."

                        with st.container(border=True):
                            st.markdown("### 🎯 Executive Overview")
                            st.write(get_synth("OVERVIEW", "PATTERNS"))
                        
                        with st.container(border=True):
                            st.markdown("### 📈 Cross-Study Patterns")
                            st.write(get_synth("PATTERNS", "CONTRADICTIONS"))
                        
                        with st.container(border=True):
                            st.markdown("### ⚖️ Conflicts & Contradictions")
                            st.write(get_synth("CONTRADICTIONS", "FUTURE_DIRECTIONS"))
                        
                        with st.container(border=True):
                            st.markdown("### 🚀 Future Research Directions")
                            st.write(get_synth("FUTURE_DIRECTIONS"))
            
            st.divider()
            if st.button("🗑️ Clear Buddy's Memory", type="secondary"):
                st.session_state.master_data = []
                st.session_state.processed_filenames = set()
                st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)
