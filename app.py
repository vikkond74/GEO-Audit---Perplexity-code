import streamlit as st
import requests
import tldextract

st.set_page_config(page_title="🧠 Perplexity GEO Audit", layout="wide")

st.title("🧠 GEO Audit Tool")
st.markdown("Perplexity API → Instant GEO recommendations with citations")

if "key" not in st.session_state:
    st.session_state.key = ""

with st.sidebar:
    st.header("🔑 Perplexity API Key")
    key_input = st.text_input("From perplexity.ai/settings/api", 
                             value=st.session_state.key, type="password")
    if st.button("✅ Save") or key_input != st.session_state.key:
        st.session_state.key = key_input
        st.rerun()
    
    if st.session_state.key:
        st.success("✅ Connected!")
    else:
        st.warning("⚠️ Add API key")

domain = st.text_input("Domain to audit", value="perplexity.ai")
model = st.selectbox("Model", [
    "llama-3.1-sonar-small-128k-online",
    "llama-3.1-sonar-large-128k-online", 
    "llama-3.1-sonar-huge-128k-online",
    "sonnet-4-mini", 
    "gpt-4o-mini"
])  # VALID models [web:81]

if st.button("🚀 Run GEO Audit", type="primary") and st.session_state.key:
    
    parsed = tldextract.extract(domain)
    site = f"{parsed.domain}.{parsed.suffix}"
    
    prompt = f"""**GEO Audit for {site}**

Complete Generative Engine Optimization analysis:
1. **Score 1-10** (current GEO readiness)
2. **Strengths** (2-3 bullets) 
3. **Issues** (4-5 bullets)
4. **Fixes** (6 numbered, specific: "Add FAQPage schema...")
5. Cite sources

Check: schema markup, FAQ structure, entity signals, citations, statistics for LLMs."""

    headers = {
        "Authorization": f"Bearer {st.session_state.key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 1600,
        "temperature": 0.1,
        "stream": False
    }

    with st.spinner("🤖 Perplexity analyzing..."):
        resp = requests.post("https://api.perplexity.ai/chat/completions",
                           headers=headers, json=payload, timeout=30)
        
        if resp.status_code == 200:
            result = resp.json()["choices"][0]["message"]["content"]
            
            st.subheader("📊 GEO Audit Report")
            st.markdown(result)
            
            st.subheader("🔍 Site Info")
            st.json({
                "domain": site,
                "model_used": model
            })
            
        else:
            st.error(f"API Error {resp.status_code}")
            st.code(resp.text)
else:
    st.info("👈 Enter API key → Get audit")

st.markdown("---")
st.caption("🆓 Pro = $5/mo credit | Models from docs.perplexity.ai")
