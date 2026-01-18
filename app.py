import streamlit as st
import asyncio
import httpx
from bs4 import BeautifulSoup
import requests
import tldextract
import json

st.set_page_config(page_title="🧠 Perplexity GEO Audit", layout="wide")

st.title("🧠 GEO Audit with Perplexity API")
st.markdown("Uses Perplexity's Sonar models with citations for authoritative GEO analysis.")

# Sidebar for Perplexity API key
with st.sidebar:
    st.header("🔑 Perplexity API Key")
    api_key = st.text_input("From perplexity.ai/settings/api", type="password", 
                           help="Settings → API tab → Generate API Key")
    if api_key:
        st.secrets["PERPLEXITY_API_KEY"] = api_key
        st.success("✅ Ready!")
        st.rerun()
    st.info("Get key: [perplexity.ai/settings/api](https://www.perplexity.ai/settings/api)")

# Main inputs
col1, col2 = st.columns(2)
with col1:
    domain = st.text_input("Domain", value="perplexity.ai")
with col2:
    model = st.selectbox("Sonar Model", ["sonar-small-online", "sonar-medium-online", "llama-3.1-sonar-small-128k-online"])

if st.button("🚀 Run Perplexity GEO Audit", type="primary") and st.secrets.get("PERPLEXITY_API_KEY"):
    
    # Step 1: Quick page crawl
    @st.cache_data(ttl=600)
    def crawl_domain(url):
        async def fetch_pages():
            base = url.rstrip('/')
            urls = [base, f"{base}/about", f"{base}/blog", f"{base.rstrip('/')}/pricing"]
            async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
                results = await asyncio.gather(*[client.get(u) for u in urls[:4]], return_exceptions=True)
                return [(u, r.text if not isinstance(r, Exception) else None) for u, r in zip(urls[:4], results)]
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(fetch_pages())

    if not domain.startswith("http"):
        domain_url = f"https://{domain}"
    else:
        domain_url = domain

    with st.spinner("🔍 Crawling site..."):
        pages = crawl_domain(domain_url)
    
    # Extract signals
    signals = []
    for url, html in pages:
        if html:
            soup = BeautifulSoup(html, "html.parser")
            signals.append({
                "url": url,
                "title": soup.title.get_text(strip=True)[:100] if soup.title else "No title",
                "h1s": len(soup.find_all("h1")),
                "schema": len(soup.find_all("script", {"type": "application/ld+json"})),
                "faq": bool(soup.find(string=lambda t: "faq" in (t or "").lower())),
                "meta_desc": bool(soup.find("meta", {"name": "description"}))
            })

    domain_info = tldextract.extract(domain_url)

    # Step 2: Perplexity API call
    with st.spinner("🤖 Perplexity analyzing..."):
        headers = {
            "Authorization": f"Bearer {st.secrets['PERPLEXITY_API_KEY']}",
            "Content-Type": "application/json"
        }
        
        prompt = f"""
Perform a **Generative Engine Optimization (GEO) audit** for:

Domain: {domain_url}
TLD: {domain_info.suffix}
Pages crawled: {len(signals)}

Page signals:
{json.dumps(signals, indent=2)}

**Output format:**
1. **GEO Score (1-10):** [score]
2. **Strengths:** [2-3 bullet points]
3. **Critical Issues:** [3-5 bullet points]  
4. **Priority Fixes:** [5 numbered recommendations with specific actions]
5. **Citations:** Use web search for GEO best practices

Focus on: schema markup, FAQ patterns, entity clarity, answerability, structured data for LLMs.
        """

        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 2000,
            "temperature": 0.3
        }

        resp = requests.post(
            "https://api.perplexity.ai/chat/completions", 
            headers=headers, 
            json=payload
        )
        
        if resp.status_code == 200:
            result = resp.json()
            audit = result["choices"][0]["message"]["content"]
            
            st.subheader("📊 Perplexity GEO Audit")
            st.markdown(audit)
            
            # Raw signals
            st.subheader("🔍 Page Data")
            st.json(signals)
            
            st.subheader("🌐 Domain Info")
            st.json({"domain": domain_info.domain, "tld": domain_info.suffix})
            
        else:
            st.error(f"API Error {resp.status_code}: {resp.text}")
else:
    st.info("👈 Add Perplexity API key to run audit")

st.markdown("---")
st.caption("Powered by [Perplexity Sonar API](https://www.perplexity.ai/settings/api) | Pro users get $5/mo free credit")
