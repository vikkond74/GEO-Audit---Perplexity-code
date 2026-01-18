import os
import asyncio
import httpx
import streamlit as st
from bs4 import BeautifulSoup
import tldextract
from openai import AsyncOpenAI

# Config
client = AsyncOpenAI(api_key=st.secrets.get("OPENAI_API_KEY", ""))
USER_AGENT = "GEO-Audit-Streamlit/1.0"

# Helpers
async def fetch_html(url: str, timeout: int = 10) -> str:
    headers = {"User-Agent": USER_AGENT}
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        resp = await client.get(url, headers=headers)
        resp.raise_for_status()
        return resp.text

def parse_basic_page_signals(html: str, url: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    title_tag = soup.find("title")
    meta_desc = soup.find("meta", attrs={"name": "description"})
    h1 = soup.find("h1")
    faqs = soup.find_all(["details", "summary"])
    schemas = [s.get_text(strip=True) for s in soup.find_all("script", type="application/ld+json")]
    text = soup.get_text(separator=" ", strip=True)
    return {
        "url": url,
        "title": title_tag.get_text(strip=True) if title_tag else None,
        "meta_description": meta_desc.get("content").strip() if meta_desc else None,
        "h1": h1.get_text(strip=True) if h1 else None,
        "has_faq_like_elements": len(faqs) > 0,
        "schema_blocks_count": len(schemas),
        "text_snippet": text[:800],
    }

def get_domain_info(domain: str) -> dict:
    """Simplified domain info (no whois)"""
    ext = tldextract.extract(domain)
    return {
        "domain": f"{ext.domain}.{ext.suffix}",
        "subdomain": ext.subdomain,
        "tld": ext.suffix,
    }

async def generate_geo_audit(company_name: str, domain: str, page_signals: list[dict], domain_info: dict) -> str:
    summary_lines = [f"- URL: {p['url']}\n  Title: {p.get('title')}\n  H1: {p.get('h1')}\n  Meta: {bool(p.get('meta_description'))}\n  FAQ: {p.get('has_faq_like_elements')}\n  Schema: {p.get('schema_blocks_count')}\n  Text: {p.get('text_snippet')}\n" for p in page_signals]
    
    messages = [
        {"role": "system", "content": "You are a Generative Engine Optimization (GEO) expert. Audit sites for AI search readiness. Be concise and actionable."},
        {"role": "user", "content": f"""
Company: {company_name}
Domain: {domain}
Domain info: {domain_info}

Page signals:
{chr(10).join(summary_lines)}

1. Assess GEO readiness (2-3 sentences).
2. List 3-5 critical issues.
3. Give 5-10 prioritized GEO recommendations.
        """}
    ]
    
    resp = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        max_tokens=1200,
        temperature=0.3
    )
    return resp.choices[0].message.content

# UI
st.set_page_config(page_title="🧠 GEO Audit", layout="wide")
st.title("🧠 Generative Engine Optimization Audit")

# Sidebar
with st.sidebar:
    st.header("🔑 OpenAI API Key")
    api_key = st.text_input("Paste your key here", type="password", help="Required for GEO analysis")
    if api_key:
        st.secrets["OPENAI_API_KEY"] = api_key
        st.success("✅ Key saved!")
    else:
        st.warning("⚠️ Add API key to enable full analysis")

if st.button("🚀 Run GEO Audit", type="primary"):
    if not st.secrets.get("OPENAI_API_KEY"):
        st.error("⚠️ Add OpenAI API key in sidebar!")
        st.stop()
    
    company_or_domain = st.text_input("Company/domain", value="perplexity.ai")
    extra_urls_raw = st.text_area("Extra URLs (one per line)", height=80)
    
    try:
        # Resolve domain
        value = company_or_domain.strip()
        if value.startswith(("http://", "https://")):
            domain_url = value
        elif "." in value:
            domain_url = "https://" + value
        else:
            st.error("Enter domain like 'example.com'")
            st.stop()

        urls_to_check = [domain_url]
        if extra_urls_raw.strip():
            urls_to_check.extend([line.strip() for line in extra_urls_raw.splitlines() if line.strip()])

        with st.spinner("🔍 Fetching pages..."):
            tasks = [fetch_html(u) for u in urls_to_check[:5]]
            html_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        page_signals = []
        for url, html in zip(urls_to_check[:5], html_results):
            if isinstance(html, Exception):
                continue
            sig = parse_basic_page_signals(html, url)
            page_signals.append(sig)

        if not page_signals:
            st.error("No pages fetched.")
            st.stop()

        domain_info = get_domain_info(domain_url)

        with st.spinner("🤖 Generating GEO audit..."):
            geo_audit_text = await generate_geo_audit(
                company_name=company_or_domain,
                domain=domain_url,
                page_signals=page_signals,
                domain_info=domain_info,
            )

        # Results
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("📊 GEO Audit Report")
            st.markdown(geo_audit_text)
        
        with col2:
            st.subheader("📈 Page Metrics")
            for p in page_signals:
                with st.expander(p["url"]):
                    col_a, col_b, col_c = st.columns(3)
                    col_a.metric("Schema", p["schema_blocks_count"])
                    col_b.metric("FAQ", "✅" if p["has_faq_like_elements"] else "❌")
                    col_c.metric("Meta", "✅" if p.get("meta_description") else "❌")
            
            st.subheader("🔍 Domain Info")
            st.json(domain_info)

    except Exception as e:
        st.error(f"Error: {e}")
