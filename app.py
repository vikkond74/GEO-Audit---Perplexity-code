import streamlit as st
import asyncio
import httpx
from bs4 import BeautifulSoup
from openai import AsyncOpenAI
import tldextract

# Page config
st.set_page_config(page_title="🧠 GEO Audit", layout="wide")

# Config
client = AsyncOpenAI(api_key=st.secrets.get("OPENAI_API_KEY", ""))

st.title("🧠 Generative Engine Optimization Audit")
st.markdown("Enter a domain → get GEO analysis powered by AI.")

# Sidebar
with st.sidebar:
    st.header("🔑 OpenAI API Key")
    api_key = st.text_input("Paste your key", type="password", help="Required")
    if api_key:
        st.secrets["OPENAI_API_KEY"] = api_key
        st.success("✅ Saved!")
        st.rerun()
    else:
        st.warning("⚠️ Add key first")

# Main app
if "results" not in st.session_state:
    st.session_state.results = None

col1, col2 = st.columns([2, 1])
with col1:
    domain_input = st.text_input("Domain (e.g. perplexity.ai)", value="perplexity.ai")
with col2:
    if st.button("🚀 Run Audit", type="primary", use_container_width=True):
        st.session_state.results = "running"

if st.session_state.results == "running" and st.secrets.get("OPENAI_API_KEY"):
    try:
        # Resolve domain
        if not domain_input.startswith("http"):
            domain_url = f"https://{domain_input.strip()}"
        else:
            domain_url = domain_input.strip()

        # Async fetch (wrapped properly)
        @st.cache_data(ttl=300)
        def fetch_pages(url):
            async def _fetch():
                urls = [url, f"{url.rstrip('/')}/about", f"{url.rstrip('/')}/blog"]
                async with httpx.AsyncClient(follow_redirects=True) as client:
                    results = await asyncio.gather(*[client.get(u, timeout=10) for u in urls], return_exceptions=True)
                    return [(u, r.text if not isinstance(r, Exception) else None) for u, r in zip(urls, results)]
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(_fetch())

        page_data = fetch_pages(domain_url)
        page_signals = []

        for url, html in page_data:
            if html:
                soup = BeautifulSoup(html, "html.parser")
                page_signals.append({
                    "url": url,
                    "title": soup.title.get_text(strip=True) if soup.title else "No title",
                    "h1_count": len(soup.find_all("h1")),
                    "schema_count": len(soup.find_all("script", {"type": "application/ld+json"})),
                    "has_faq": bool(soup.find("details") or soup.find_all(string=lambda t: "faq" in t.lower())),
                    "word_count": len(soup.get_text().split())
                })

        # Domain info
        domain_info = tldextract.extract(domain_url)
        
        # LLM audit
        @st.cache_data(ttl=1800)
        def get_geo_audit(domain_url, page_signals, domain_info):
            messages = [{
                "role": "user", 
                "content": f"""
GEO Audit Request:

Domain: {domain_url}
Domain info: {domain_info._asdict()}
Pages analyzed: {len(page_signals)}

Page signals:
{chr(10).join([f"- {p['url']}: schema={p['schema_count']}, H1s={p['h1_count']}, words={p['word_count']}, FAQ={p['has_faq']}" for p in page_signals])}

Give:
1. GEO readiness score (1-10)
2. 3 critical issues
3. 5 prioritized fixes
                """
            }]
            
            resp = client.chat.completions.create(model="gpt-4o-mini", messages=messages, max_tokens=1000)
            return resp.choices[0].message.content

        geo_report = get_geo_audit(domain_url, page_signals, domain_info)

        # Display results
        st.session_state.results = "done"

        st.subheader("🤖 GEO Audit Report")
        st.markdown(geo_report)

        st.subheader("📊 Page Analysis")
        for signal in page_signals:
            with st.expander(signal["url"]):
                st.json(signal)

        st.subheader("🔍 Domain")
        st.json({"domain": domain_info.domain, "tld": domain_info.suffix})

    except Exception as e:
        st.error(f"Error: {e}")
        st.exception(e)
        st.session_state.results = None

elif not st.secrets.get("OPENAI_API_KEY"):
    st.info("👈 Add your OpenAI API key in the sidebar to start!")
