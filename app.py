import streamlit as st
import pandas as pd
from pypdf import PdfReader
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
import re


# 1. PAGE CONFIGURATION
st.set_page_config(page_title="PhD Research Extractor", layout="wide")

# 2. STYLING (CSS) - FIXED SPACING
st.markdown("""
    <style>
    [data-testid="stHeader"] { background-color: rgba(255, 255, 255, 0); }
    
    .sticky-wrapper {
        position: fixed; top: 0; left: 0; width: 100%;
        background-color: white; z-index: 1000;
        padding: 15px 50px 0px 50px; /* Thinner header padding */
        border-bottom: 2px solid #f0f2f6;
    }
    
    .main-content { 
        margin-top: 5px; /* DRASTICALLY reduced to close the gap */
    }

    /* Remove default Streamlit top padding */
    .block-container {
        padding-top: 1rem !important;
    }

    [data-testid="stFileUploaderContainer"] section { padding: 0px !important; width: 100% !important; }
    
    div.stButton > button:first-child {
        width: 100% !important; color: #28a745 !important;
        border: 2px solid #28a745 !important; font-weight: bold !important;
        margin-top: 5px; background-color: transparent !important;
    }
    .section-title { font-weight: bold; color: #1f77b4; margin-top: 20px; display: block; text-transform: uppercase; font-size: 0.85rem; border-bottom: 1px solid #eee; }
    .section-content { display: block; margin-bottom: 15px; line-height: 1.7; color: #333; }
    </style>
    """

# 3. AUTHENTICATION LOGIC (SECRETS)
def check_password():
    """Returns True if the user had the correct password."""
    # This pulls from the 'APP_PASSWORD' you set in the Streamlit Cloud Secrets dashboard
    correct_password = st.secrets.get("APP_PASSWORD")
    
    if "password_correct" not in st.session_state:
        st.markdown("### 🔒 Research Gateway")
        pwd = st.text_input("Enter Access Password", type="password")
        if st.button("Unlock Tool"):
            if pwd == correct_password:
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("🚫 Access Denied: Incorrect Password")
        return False
    return True

# 4. MAIN APPLICATION
if check_password():
    # Fetch API Key from Secrets
    api_key = st.secrets.get("GEMINI_API_KEY")

    # State Management
    if 'master_data' not in st.session_state: st.session_state.master_data = [] 
    if 'processed_filenames' not in st.session_state: st.session_state.processed_filenames = set() 

    st.markdown('<div class="sticky-wrapper"><h1 style="margin:0;">🎓 PhD Research Extractor</h1><p style="color:gray; margin-bottom:10px;">PhD Reviewer Mode | Gemini 2.0 Flash</p></div>', unsafe_allow_html=True)

    with st.container():
        st.markdown('<div class="main-content">', unsafe_allow_html=True)
        
        # Initialize AI
        llm = None
        if api_key:
            llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", google_api_key=api_key, temperature=0.1)
        else:
            st.warning("⚠️ GEMINI_API_KEY not found in Secrets dashboard.")

        st.divider()
        uploaded_files = st.file_uploader("Upload academic papers (PDF)", type="pdf", accept_multiple_files=True)
        run_review = st.button("🔬 Execute Full-Text Review", use_container_width=True)

        # Processing Loop
        if uploaded_files and llm and run_review:
            progress_text = st.empty()
            for file in uploaded_files:
                if file.name in st.session_state.processed_filenames: continue
                progress_text.text(f"Analyzing: {file.name}...")
                try:
                    reader = PdfReader(file) 
                    full_text = "".join([page.extract_text() for page in reader.pages if page.extract_text()]).strip()
                    
                    if not full_text: continue

                    prompt = f"""
                    PhD-level extraction requested. Cohesive paragraphs only.
                    Markers: [TITLE], [AUTHORS], [YEAR], [REFERENCE], [SUMMARY], [BACKGROUND], [METHODOLOGY], [CONTEXT], [FINDINGS], [RELIABILITY].
                    
                    TEXT: {full_text[:30000]}
                    """
                    
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

        # Display Results
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
                # FIXED: Row index (0,1) is hidden so it matches the '#' column
                df = pd.DataFrame(st.session_state.master_data)
                st.dataframe(df, use_container_width=True, hide_index=True)
            
            with t3:
                if llm:
                    findings_list = [f"P{r['#']} ({r['Title']}): {r['Findings']}" for r in st.session_state.master_data]
                    with st.spinner("Synthesizing..."):
                        synth_query = "Perform a PhD-level synthesis of these results:\n\n" + "\n\n".join(findings_list)
                        st.markdown(llm.invoke([HumanMessage(content=synth_query)]).content)

        st.markdown('</div>', unsafe_allow_html=True)
