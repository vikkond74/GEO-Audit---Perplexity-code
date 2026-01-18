import streamlit as st
import asyncio
import httpx
from bs4 import BeautifulSoup
import requests
import tldextract
import json

st.set_page_config(page_title="🧠 Perplexity GEO Audit", layout="wide")

st.title("🧠 GEO Audit - Perplexity Edition")
st.markdown("Domain → Perplexity Sonar analysis → Actionable GEO recommendations")

# API Key input (session state instead of secrets write)
if "api_key" not in st.session_state:
    st.session_state.api_key = ""

with st.sidebar:
    st.header("🔑 Perplexity API")
    new_key = st.text_input("API Key", value=st.session_state.api_key, type="password",
                           help="perplexity.ai/settings/api → Generate")
    if st.button("✅ Save Key") or new_key != st.session_state.api_key:
        st.session_state.api_key = new_key
        st.rerun()
    
    if st.session_state.api_key:
        st.success("✅ Key loaded")
        st.caption("Sonar models: web search + citations")
    else:
        st.warning("⚠️ Add key to run audits")

# Main UI
col1, col2 = st.columns([3, 1])
with col1:
    domain = st.text_input("Domain", value="perplexity.ai")
with col2:
    model = st.selectbox("Model", 
                        ["sonar-small-online", "sonar-medium-online", "llama-3.1-sonar-small-128k-online"])

if st.button("🚀 Run Perplexity GEO Audit", type="primary") and st.session_state.api_key:
    
    if not domain.startswith("http"):
        domain_url = f"https://{domain.strip()}"
    else:
        domain_url = domain.strip()

    # 1. Crawl (cached)
    @st.cache_data(ttl=600)
    def crawl_site(url):
        async def fetch():
            base = url.rstrip('/')
            urls = [base, f"{base}/about", f"{base}/blog", f"{base}/pricing"][:4]
            async with httpx.AsyncClient(timeout=12, follow_redirects=True) as client:
                results = await asyncio.gather(*[client.get(u) for u in urls], return_exceptions=True)
                return [(u, r.text if not isinstance(r, Exception) else None) for u, r in zip(urls, results)]
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(fetch())

    with st.spinner("🔍 Analyzing site structure..."):
        pages = crawl_site(domain_url)
        signals = []
        
        for url, html in pages:
            if html:
                soup = BeautifulSoup(html, "html.parser")
                signals.append({
                    "url": url,
                    "title": soup.title.get_text(strip=True)[:80] if soup.title else "No title",
                    "h1_count": len(soup.find_all("h1")),
                    "schema_count": len(soup.find_all("script", {"type": "application/ld+json"})),
                    "has_faq": len([t for t in soup.stripped_strings if "faq" in t.lower()]) > 0,
                    "meta_desc": bool(soup.find("meta", {"name": "description"})),
                    "word_count": len(soup.get_text().split())
                })

    domain_parts = tldextract.extract(domain_url)

    # 2. Perplexity API
    @st.cache_data(ttl=1800)
    def perplexity_geo_audit(domain_url, signals, model_choice):
        headers = {
            "Authorization": f"Bearer {st.session_state.api_key}",
            "Content-Type": "application/json"
        }
        
        prompt = f"""**GEO Audit for {domain_url}**

Domain info: {domain_parts._asdict()}
Pages analyzed: {len(signals)}

Page signals:
{json.dumps(signals, indent=2)}

**Required output:**
1. **GEO Score (1-10):** 
2. **Strengths** (2 bullets)
3. **Critical Issues** (3-5 bullets)  
4. **Priority Fixes** (5 numbered, specific actions like "Add FAQ schema to /pricing")
5. **Web citations** for recommendations

GEO focus: schema, FAQs, entity clarity, LLM answerability, structured data."""

        payload = {
            "model": model_choice,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 1800,
            "temperature": 0.2
        }

        resp = requests.post("https://api.perplexity.ai/chat/completions", 
                           headers=headers, json=payload, timeout=30)
        
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"]
        return f"API Error {resp.status_code}: {resp.text[:200]}"

    with st.spinner("🤖 Perplexity Sonar analyzing..."):
        geo_report = perplexity_geo_audit(domain_url, signals, model)

    # Results
    st.subheader("📊 Perplexity GEO Report")
    st.markdown(geo_report)

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("🔍 Page Signals")
        st.json(signals)
    
    with c2:
        st.subheader("🌐 Domain")
        st.json({
            "domain": domain_parts.domain,
            "tld": domain_parts.suffix,
            "subdomain": domain_parts.subdomain or "none"
        })

    st.balloons()

else:
    st.info("👈 Enter Perplexity API key → Run audit")
    st.markdown("[Get API key](https://www.perplexity.ai/settings/api)")

st.markdown("---")
st.caption("🦾 Perplexity Pro = $5/mo free API credit | Sonar models auto-cite web sources")
