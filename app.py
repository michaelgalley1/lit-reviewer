import streamlit as st
import pandas as pd
from pypdf import PdfReader
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
import re
import time

# 1. PAGE CONFIGURATION
st.set_page_config(page_title="Literature Review Buddy", page_icon="📚", layout="wide")

# 2. BRANDED STYLING (CSS)
st.markdown("""
    <style>
    /* Load Custom Fonts */
    @import url('https://fonts.googleapis.com/css2?family=REM:wght@600;800&display=swap');
    
    /* Global Styles */
    html, body, [class*="css"] {
        font-family: 'Averta', 'Century Gothic', sans-serif;
        background-color: #F7EFDE; /* Stone */
        color: #000000; /* Black */
    }

    /* Titles and Headers */
    h1, h2, h3, .section-title {
        font-family: 'REM', sans-serif !important;
        color: #0000FF !important; /* Blue */
    }

    [data-testid="stHeader"] { background-color: rgba(0,0,0,0); }
    
    .sticky-wrapper {
        position: fixed; top: 0; left: 0; width: 100%;
        background-color: #FFFFFF; z-index: 1000;
        padding: 15px 50px 10px 50px;
        border-bottom: 3px solid #97D9E3; /* Sea */
    }
    
    .main-content { 
        margin-top: -65px; 
    }

    .block-container {
        padding-top: 0rem !important;
        background-color: #F7EFDE; /* Stone */
    }

    /* File Uploader Customization */
    [data-testid="stFileUploader"] { 
        padding-top: 0px !important; 
        background-color: #FFFFFF;
        border-radius: 10px;
        padding: 10px;
        border: 2px dashed #97D9E3;
    }
    
    /* Analyse Button - Green/Sea Theme */
    div.stButton > button:first-child {
        width: 100% !important; 
        color: #FFFFFF !important;
        background-color: #18A48C !important; /* Green */
        border: none !important;
        font-family: 'REM', sans-serif !important;
        font-size: 1.1rem !important;
        border-radius: 8px !important;
        transition: 0.3s;
    }
    div.stButton > button:hover {
        background-color: #0000FF !important; /* Blue on hover */
    }

    /* Tabs Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #FFFFFF;
        border-radius: 5px 5px 0 0;
        padding: 10px 20px;
        color: #000000;
    }
    .stTabs [aria-selected="true"] {
        background-color: #97D9E3 !important; /* Sea */
        border-bottom: 3px solid #0000FF !important;
    }

    /* Buddy Cards */
    [data-testid="stExpander"], div[data-testid="stVerticalBlock"] > div[style*="border: 1px solid"] {
        background-color: #FFFFFF !important;
        border: 1px solid #97D9E3 !important;
        border-radius: 12px !important;
        box-shadow: 4px 4px 0px #A59BEE; /* Violet Shadow */
    }

    .section-title { 
        font-weight: 800; 
        margin-top: 15px; 
        display: block; 
        text-transform: uppercase; 
        font-size: 0.8rem; 
        letter-spacing: 1px;
    }
    .section-content { 
        display: block; 
        margin-bottom: 10px; 
        line-height: 1.6; 
        color: #333333; 
        font-family: 'Averta', 'Century Gothic', sans-serif;
    }

    /* Metric/Ref Circle */
    [data-testid="stMetricValue"] {
        color: #9A1BBE !important; /* Purple */
        font-family: 'REM', sans-serif !important;
    }
    </style>
    """, unsafe_allow_html=True)

# 3. AUTHENTICATION
def check_password():
    correct_password = st.secrets.get("APP_PASSWORD")
    if "password_correct" not in st.session_state:
        st.markdown("<h3 style='text-align:center;'>📚 Literature Review Buddy</h3>", unsafe_allow_html=True)
        pwd = st.text_input("Enter Access Password", type="password")
        if st.button("Unlock Buddy"):
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
            <h1 style="margin:0; font-size: 1.8rem; font-family: 'REM', sans-serif;">📚 Literature Review Buddy</h1>
            <p style="color:#18A48C; font-weight: bold; margin-bottom:5px; font-family: 'Averta', sans-serif;">Your PhD-Level Research Assistant</p>
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
                    for s in range(3, 0, -1):
                        progress_text.text(f"⏳ Buddy is taking a breath... {s}s")
                        time.sleep(1)

                progress_text.text(f"📖 Buddy is reading the full text: {file.name}...")
                try:
                    reader = PdfReader(file) 
                    text = "".join([p.extract_text() for p in reader.pages if p.extract_text()]).strip()
                    
                    prompt = f"""
                    You are a senior academic researcher. Analyze the ATTACHED FULL TEXT with extreme rigor.
                    Use plain text only. No asterisks (**), no bolding.
                    Labels: [TITLE], [AUTHORS], [YEAR], [REFERENCE], [SUMMARY], [BACKGROUND], [METHODOLOGY], [CONTEXT], [FINDINGS], [RELIABILITY].
                    FULL TEXT: {text}
                    """
                    
                    res = llm.invoke([HumanMessage(content=prompt)]).content
                    res = re.sub(r'\*', '', res) 

                    def ext(label, next_l=None):
                        p = rf"\[{label}\]:?\s*(.*?)(?=\s*\[{next_l}\]|$)" if next_l else rf"\[{label}\]:?\s*(.*)"
                        m = re.search(p, res, re.DOTALL | re.IGNORECASE)
                        return m.group(1).strip() if m else "Analysis pending..."

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
                        cr, ct = st.columns([1, 12]); cr.metric("REF", r['#']); ct.subheader(r['Title'])
                        st.markdown(f"<p style='color:#9A1BBE; font-size:0.9rem;'>{r['Authors']} ({r['Year']})</p>", unsafe_allow_html=True)
                        st.divider()
                        sec = [("Summary", r["Summary"]), ("📖 Background", r["Background"]), ("⚙️ Methodology", r["Methodology"]), ("📍 Context", r["Context"]), ("💡 Findings", r["Findings"]), ("🛡️ Reliability", r["Reliability"])]
                        for k, v in sec:
                            st.markdown(f'<span class="section-title">{k}</span><span class="section-content">{v}</span>', unsafe_allow_html=True)
            
            with t2:
                st.dataframe(pd.DataFrame(st.session_state.master_data), use_container_width=True, hide_index=True)
            
            with t3:
                if llm:
                    f_list = [f"Paper {r['#']}: {r['Findings']}" for r in st.session_state.master_data]
                    with st.spinner("Buddy is thinking..."):
                        synth_prompt = f"Meta-synthesis of these findings (No asterisks, use labels [OVERVIEW], [PATTERNS], [CONTRADICTIONS], [FUTURE_DIRECTIONS]):\n\n" + " / ".join(f_list)
                        raw_synth = llm.invoke([HumanMessage(content=synth_prompt)]).content
                        clean_synth = re.sub(r'\*', '', raw_synth)

                        def get_synth(label, next_l=None):
                            p = rf"\[{label}\]:?\s*(.*?)(?=\s*\[{next_l}\]|$)" if next_l else rf"\[{label}\]:?\s*(.*)"
                            m = re.search(p, clean_synth, re.DOTALL | re.IGNORECASE)
                            return m.group(1).strip() if m else "Detail not found."

                        col1, col2 = st.columns(2)
                        with col1:
                            with st.container(border=True):
                                st.markdown("### 🎯 Overview")
                                st.write(get_synth("OVERVIEW", "PATTERNS"))
                            with st.container(border=True):
                                st.markdown("### ⚖️ Conflicts")
                                st.write(get_synth("CONTRADICTIONS", "FUTURE_DIRECTIONS"))
                        with col2:
                            with st.container(border=True):
                                st.markdown("### 📈 Patterns")
                                st.write(get_synth("PATTERNS", "CONTRADICTIONS"))
                            with st.container(border=True):
                                st.markdown("### 🚀 Next Steps")
                                st.write(get_synth("FUTURE_DIRECTIONS"))
            
            st.divider()
            if st.button("🗑️ Clear Buddy's Memory", type="secondary"):
                st.session_state.master_data = []
                st.session_state.processed_filenames = set()
                st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)
