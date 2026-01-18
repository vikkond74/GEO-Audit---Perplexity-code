import streamlit as st
import asyncio
import httpx
from bs4 import BeautifulSoup
import requests
import tldextract

st.set_page_config(page_title="🧠 Perplexity GEO Audit", layout="wide")

st.title("🧠 GEO Audit - Perplexity Sonar")
st.markdown("Domain analysis → Perplexity AI audit → Actionable recommendations")

# Session state for API key
if "api_key" not in st.session_state:
    st.session_state.api_key = ""

with st.sidebar:
    st.header("🔑 Perplexity API Key")
    new_key = st.text_input("Paste key here", value=st.session_state.api_key, type="password")
    if st.button("Save Key") or new_key != st.session_state.api_key:
        st.session_state.api_key = new_key
        st.rerun()
    
    if st.session_state.api_key:
        st.success("✅ Ready to audit!")
    else:
        st.warning("Add key first")

col1, col2 = st.columns([3,1])
with col1:
    domain = st.text_input("Domain", value="perplexity.ai")
with col2:
    model = st.selectbox("Model", ["sonar-small-online", "sonar-medium-online"])

if st.button("🚀 Run Audit", type="primary") and st.session_state.api_key:
    
    # Normalize URL
    if not domain.startswith("http"):
        url = f"https://{domain.strip()}"
    else:
        url = domain.strip()

    # 1. Crawl pages
    @st.cache_data(ttl=600)
    def get_pages(base_url):
        async def fetch():
            paths = ["", "/about", "/blog", "/pricing"][:3]
            urls = [f"{base_url.rstrip('/')}{p}" for p in paths]
            async with httpx.AsyncClient(timeout=10) as client:
                results = await asyncio.gather(*[client.get(u) for u in urls], return_exceptions=True)
                return [(u, r.text if not isinstance(r, Exception) else None) for u, r in zip(urls, results)]
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(fetch())

    pages = get_pages(url)
    signals = []
    
    for page_url, html in pages:
        if html:
            soup = BeautifulSoup(html, "html.parser")
            signals.append({
                "url": page_url,
                "title": soup.title.get_text(strip=True)[:60] if soup.title else "?",
                "h1s": len(soup.find_all("h1")),
                "schema": len(soup.find_all("script", type="application/ld+json")),
                "faq": "faq" in soup.get_text().lower(),
                "desc": bool(soup.find("meta", attrs={"name": "description"}))
            })

    # Domain parse
    domain_info = tldextract.extract(url)
    domain_dict = {
        "domain": domain_info.domain,
        "tld": domain_info.suffix,
        "subdomain": domain_info.subdomain or "none"
    }

    # 2. Perplexity call
    @st.cache_data(ttl=1800)
    def call_perplexity(full_url, sigs, model_name, api_key, dom_info):
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        prompt = f"""**GEO Audit Request**

Site: {full_url}
Domain: {dom_info['domain']}.{dom_info['tld']}
Pages: {len(sigs)}

Signals:
{str(sigs)}

**Format:**
1. GEO Score (1-10)
2. Strengths (2 bullets)  
3. Issues (3-5 bullets)
4. Fixes (5 numbered actions)
5. Cite GEO sources

Focus: schema, FAQ structure, entity signals for LLMs."""

        payload = {
            "model": model_name,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 1500,
            "temperature": 0.2
        }

        resp = requests.post("https://api.perplexity.ai/chat/completions", 
                           headers=headers, json=payload, timeout=30)
        
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"]
        return f"Error {resp.status_code}"

    with st.spinner("🤖 Perplexity analyzing..."):
        report = call_perplexity(url, signals, model, st.session_state.api_key, domain_dict)

    # Results layout
    st.subheader("📊 Perplexity GEO Report")
    st.markdown(report)

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📈 Page Metrics")
        for sig in signals:
            st.metric(sig["url"][-30:], f"H1: {sig['h1s']}", f"Schema: {sig['schema']}")
    
    with col2:
        st.subheader("🔍 Domain Info")
        st.json(domain_dict)

else:
    st.info("👈 Enter Perplexity API key → Run audit")

st.markdown("---")
st.caption("Perplexity Pro = $5/mo free API | Sonar = web search + citations")
