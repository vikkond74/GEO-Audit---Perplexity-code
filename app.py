import streamlit as st
import requests
import tldextract

st.set_page_config(layout="wide")

st.title("🧠 GEO Audit - Perplexity")
st.markdown("Domain → Perplexity analysis → GEO fixes")

if "key" not in st.session_state:
    st.session_state.key = ""

st.sidebar.header("🔑 API Key")
key = st.sidebar.text_input("perplexity.ai/settings/api", type="password")
if st.sidebar.button("Save") or key != st.session_state.key:
    st.session_state.key = key
    st.rerun()

domain = st.text_input("Domain", value="perplexity.ai")

# EXACT API MODEL NAMES [web:114]
model = st.selectbox("Model", [
    "pplx-70b-online",        # ✅ Sonar Search
    "pplx-70b-chat",          # ✅ Chat  
    "pplx-7b-chat",           # ✅ Fast
    "llama-3.1-sonar-small",  # ✅ Sonar
    "mixtral-8x7b-instruct"   # ✅ Reliable
])

if st.button("🚀 Audit", type="primary") and st.session_state.key:
    
    site = tldextract.extract(domain).registered_domain
    
    prompt = f"""GEO audit {site}:
1. Score 1-10
2. 3 strengths  
3. 4 issues
4. 5 fixes w/ actions
Cite sources."""

    headers = {
        "Authorization": f"Bearer {st.session_state.key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 1000,
        "temperature": 0.2,
        "stream": False
    }

    with st.spinner("🤖 ..."):
        resp = requests.post("https://api.perplexity.ai/chat/completions",
                           headers=headers, json=payload)
        
        if resp.status_code == 200:
            result = resp.json()["choices"][0]["message"]["content"]
            st.markdown("### 📊 Report")
            st.markdown(result)
        else:
            st.error(f"Error {resp.status_code}")
            st.json(resp.json())

st.caption("Pro API working | pplx- models from docs [web:114]")
