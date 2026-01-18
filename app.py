import streamlit as st
import requests
import tldextract

st.set_page_config(page_title="🧠 Perplexity GEO Audit", layout="wide")

st.title("🧠 GEO Audit")
st.markdown("Perplexity-powered Generative Engine Optimization analysis")

if "key" not in st.session_state:
    st.session_state.key = ""

with st.sidebar:
    st.header("🔑 API Key")
    key_input = st.text_input("perplexity.ai/settings/api", type="password", 
                             value=st.session_state.key)
    if st.button("Save") or key_input != st.session_state.key:
        st.session_state.key = key_input
        st.rerun()
    
    if st.session_state.key:
        st.success("✅ Ready")

domain = st.text_input("Domain", value="perplexity.ai")

# CORRECT models from https://docs.perplexity.ai/getting-started/models [attached_file:1]
model = st.selectbox("Model", [
    "llama-3.1-sonar-small-128k-online",
    "llama-3.1-sonar-large-online",
    "mixtral-8x7b-instruct",
    "gemma2-9b-instruct",
    "sonnet-3.5-mini"
], index=0)

if st.button("🚀 Audit", type="primary") and st.session_state.key:
    
    parsed = tldextract.extract(domain)
    site = f"{parsed.domain}.{parsed.suffix}"
    
    prompt = f"""**GEO Audit for {site}**

1. Current GEO Score (1-10)
2. 3 Strengths  
3. 4 Issues
4. 6 Specific fixes ("Add schema to /pricing...")
5. Cite sources

GEO = schema, FAQs, entities for LLMs."""

    headers = {"Authorization": f"Bearer {st.session_state.key}", 
               "Content-Type": "application/json"}
    
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 1400,
        "temperature": 0.2,
        "stream": False
    }

    with st.spinner("🤖 Analyzing..."):
        resp = requests.post("https://api.perplexity.ai/chat/completions",
                           headers=headers, json=payload, timeout=25)
        
        if resp.status_code == 200:
            report = resp.json()["choices"][0]["message"]["content"]
            st.markdown("### 📊 GEO Report")
            st.markdown(report)
            st.markdown("### 🔍 Domain")
            st.json({"site": site, "model": model})
        else:
            st.error(f"Error {resp.status_code}")
            st.json({"status": resp.status_code, "response": resp.text[:400]})
else:
    st.info("👈 Add API key")

st.caption("Pro = $5/mo free | Models from docs.perplexity.ai [attached_file:1]")
