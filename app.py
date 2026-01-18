import streamlit as st
import requests
import tldextract

st.set_page_config(page_title="🧠 Perplexity GEO Audit", layout="wide")

st.title("🧠 Instant GEO Audit")
st.markdown("Enter domain → Perplexity Sonar searches + audits → Fixes with citations")

# API key
if "key" not in st.session_state:
    st.session_state.key = ""

with st.sidebar:
    st.header("🔑 Perplexity API")
    key = st.text_input("API Key", value=st.session_state.key, type="password")
    if st.button("Save") or key != st.session_state.key:
        st.session_state.key = key
        st.rerun()
    
    if st.session_state.key:
        st.success("✅ Ready!")
        st.caption("Get key: perplexity.ai/settings/api")

domain = st.text_input("Domain", value="perplexity.ai")
model = st.selectbox("Model", ["sonar-small-online", "sonar-medium-online"])

if st.button("🚀 GEO Audit", type="primary") and st.session_state.key:
    
    # Domain info
    parsed = tldextract.extract(domain)
    domain_info = f"{parsed.domain}.{parsed.suffix}"
    
    # Perplexity prompt (no crawling needed!)
    prompt = f"""**Generative Engine Optimization (GEO) Audit**

Target: {domain} ({domain_info})

Do a complete GEO audit:
1. Check current SEO/GEO status via web search
2. GEO Score 1-10  
3. 3 Strengths
4. 5 Critical issues  
5. 8 Specific fixes (e.g. "Add Organization schema to homepage")
6. Cite sources

GEO priorities: schema markup, FAQ patterns, statistics/quotes, authoritative language, localBusiness clarity."""

    headers = {
        "Authorization": f"Bearer {st.session_state.key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 2000,
        "temperature": 0.2,
        "stream": False
    }

    with st.spinner("🤖 Perplexity searching + analyzing..."):
        resp = requests.post("https://api.perplexity.ai/chat/completions", 
                           headers=headers, json=payload, timeout=25)
        
        if resp.status_code == 200:
            report = resp.json()["choices"][0]["message"]["content"]
            
            st.subheader("📊 Perplexity GEO Report")
            st.markdown(report)
            
            st.subheader("🔍 Domain")
            st.json({"domain": domain_info, "full": domain})
            
        else:
            st.error(f"API {resp.status_code}: {resp.text[:300]}")
            st.json(payload)  # debug payload
else:
    st.info("👈 Enter API key → Audit")

st.markdown("---")
st.caption("🆓 Pro = $5/mo API credit | No crawling = instant results")
