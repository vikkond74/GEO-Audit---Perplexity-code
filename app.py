import streamlit as st
import asyncio
import httpx
from bs4 import BeautifulSoup
import requests
import tldextract

st.set_page_config(page_title="🧠 Perplexity GEO Audit", layout="wide")

st.title("🧠 GEO Audit - Perplexity")
st.markdown("Fast GEO analysis powered by Perplexity Sonar")

if "api_key" not in st.session_state:
    st.session_state.api_key = ""

with st.sidebar:
    st.header("🔑 API Key")
    new_key = st.text_input("perplexity.ai/settings/api", type="password", 
                           value=st.session_state.api_key)
    if st.button("Save") or new_key != st.session_state.api_key:
        st.session_state.api_key = new_key
        st.rerun()
    
    if st.session_state.api_key:
        st.success("✅ Ready!")
    else:
        st.warning("Add key")

col1, col2 = st.columns([3,1])
with col1:
    domain = st.text_input("Domain", value="perplexity.ai")
with col2:
    model = st.selectbox("Model", ["sonar-small-online", "sonar-medium-online"])

if st.button("🚀 Audit", type="primary") and st.session_state.api_key:
    
    url = f"https://{domain.strip().rstrip('/')}" if not domain.startswith("http") else domain.strip()
    
    # Quick crawl
    @st.cache_data(ttl=600)
    def crawl(url):
        async def get_pages():
            urls = [url, f"{url}/about", f"{url}/blog"][:3]
            async with httpx.AsyncClient(timeout=8) as c:
                r = await asyncio.gather(*[c.get(u) for u in urls])
                return [(u, r.text) for u, r in zip(urls, r)]
        loop = asyncio.new_event_loop()
        return loop.run_until_complete(get_pages())

    pages = crawl(url)
    signals = []
    for page_url, html in pages:
        soup = BeautifulSoup(html, "html.parser")
        signals.append({
            "url": page_url[-40:],
            "title": soup.title.get_text()[:50] if soup.title else "No title",
            "h1": len(soup.find_all("h1")),
            "schema": len(soup.find_all("script", type="application/ld+json"))
        })

    # Perplexity API (fixed payload)
    def perplexity_api(prompt, model_name):
        headers = {
            "Authorization": f"Bearer {st.session_state.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model_name,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 1200,
            "temperature": 0.3,
            "stream": False  # Required for non-streaming
        }
        resp = requests.post("https://api.perplexity.ai/chat/completions", 
                           headers=headers, json=payload, timeout=20)
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"]
        return f"HTTP {resp.status_code}: {resp.text[:150]}"

    prompt = f"""GEO Audit:

Domain: {url}
Pages ({len(signals)}):
{signals}

Score 1-10, list 3 issues, 5 fixes. Focus: schema/FAQ/entity clarity for AI search."""

    with st.spinner("🤖 Perplexity..."):
        report = perplexity_api(prompt, model)

    st.markdown("### 📊 GEO Report")
    st.markdown(report)
    
    st.markdown("### 📈 Data")
    st.json({"pages": signals, "domain": tldextract.extract(url).domain})

else:
    st.info("👈 Enter API key → Audit")

st.caption("Perplexity Pro = $5/mo free | [API docs](https://www.perplexity.ai/settings/api)")
