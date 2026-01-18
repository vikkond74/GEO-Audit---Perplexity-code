import streamlit as st
import requests
import tldextract

st.set_page_config(page_title="🧠 Perplexity GEO", layout="wide")

st.title("🧠 GEO Audit Tool")
st.markdown("Perplexity API → GEO analysis with citations")

if "key" not in st.session_state:
    st.session_state.key = ""

with st.sidebar:
    st.header("🔑 API Key")
    key = st.text_input("perplexity.ai/settings/api", type="password", 
                       value=st.session_state.key)
    if st.button("Save") or key != st.session_state.key:
        st.session_state.key = key
        st.rerun()

domain = st.text_input("Domain", value="perplexity.ai")

# EXACT API models [web:114][web:115]
model = st.selectbox("Model", [
    "perplexity/sonar-pro",           # ✅ Works
    "perplexity/sonar",               # ✅ Works  
    "perplexity/sonar-reasoning",     # ✅ Reasoning
    "perplexity/r1-1776",             # ✅ Latest
    "mixtral-8x7b-instruct"           # ✅ Fallback
])

if st.button("🚀 Audit", type="primary") and st.session_state.key:
    
    site = tldextract.extract(domain).registered_domain
    
    prompt = f"""GEO Audit for {site}:

1. Score 1-10
2. 3 strengths
3. 4 issues  
4. 5 fixes ("Add FAQ schema...")
5. Cite GEO best practices"""

    headers = {"Authorization": f"Bearer {st.session_state.key}", 
               "Content-Type": "application/json"}
    
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 1200,
        "temperature": 0.2,
        "stream": False
    }

    with st.spinner("Analyzing..."):
        resp = requests.post("https://api.perplexity.ai/chat/completions",
                           headers=headers, json=payload, timeout=25)
        
        if resp.status_code == 200:
            result = resp.json()["choices"][0]["message"]["content"]
            st.markdown("### 📊 Report")
            st.markdown(result)
            st.caption(f"Model: {model}")
        else:
            st.error(f"Error {resp.status_code}")
            st.json(resp.json() if resp.content else resp.text)

else:
    st.info("Add API key")

st.caption("Pro = $5/mo free | Models: perplexity/sonar-pro etc [web:114]")
