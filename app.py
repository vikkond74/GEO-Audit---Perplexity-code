import os
import asyncio
import httpx
import streamlit as st
from bs4 import BeautifulSoup
import whois
import tldextract
from openai import AsyncOpenAI  # CHANGE to your LLM provider

# Config (use Streamlit secrets)
if "OPENAI_API_KEY" not in st.secrets:
    st.secrets["OPENAI_API_KEY"] = ""  # user will add this

client = AsyncOpenAI(api_key=st.secrets["OPENAI_API_KEY"])

USER_AGENT = "GEO-Audit-Streamlit/1.0"

# ---------- Helpers (same as before) ----------
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


def get_domain_whois(domain: str) -> dict:
    try:
        w = whois.whois(domain)
        return {
            "domain_name": str(w.domain_name),
            "registrar": getattr(w, 'registrar', None),
            "creation_date": str(getattr(w, 'creation_date', None)),
            "expiration_date": str(getattr(w, 'expiration_date', None)),
            "country": getattr(w, 'country', None),
        }
    except:
        return {}


async def generate_geo_audit(company_name: str, domain: str, page_signals: list[dict], whois_info: dict) -> str:
    summary_lines = [f"- URL: {p['url']}\n  Title: {p.get('title')}\n  H1: {p.get('h1')}\n  Meta: {bool(p.get('meta_description'))}\n  FAQ: {p.get('has_faq_like_elements')}\n  Schema: {p.get('schema_blocks_count')}\n  Text: {p.get('text_snippet')}\n" for p in page_signals]
    whois_summary = f"Domain WHOIS: {whois_info}\n" if whois_info else "Domain WHOIS: unavailable\n"
    
    messages = [
        {"role": "system", "content": "You are a Generative Engine Optimization (GEO) expert. Audit sites for AI search readiness. Be concise and actionable."},
        {"role": "user", "content": f"""
Company: {company_name}
Domain: {domain}

{whois_summary}

Page signals:
{chr(10).join(summary_lines)}

1. Assess GEO readiness (2-3 sentences).
2. List 3-5 critical issues.
3. Give 5-10 prioritized GEO recommendations.
        """}
    ]
    
    resp = await client.chat.completions.create(
        model="gpt-4o-mini",  # CHANGE to your model
        messages=messages,
        max_tokens=1200,
        temperature=0.3
    )
    return resp.choices[0].message.content


# ---------- Streamlit UI ----------
st.set_page_config(page_title="🧠 GEO Audit", layout="wide")

st.title("🧠 Generative Engine Optimization Audit")
st.markdown("Enter a domain to get a GEO-focused audit powered by LLM analysis.")

# Sidebar for API key
with st.sidebar:
    st.header("🔑 API Key")
    api_key = st.text_input("OpenAI API Key", type="password", help="Required for GEO analysis")
    if api_key:
        st.secrets["OPENAI_API_KEY"] = api_key
        st.success("API key saved!")
    else:
        st.warning("Add your API key to enable LLM analysis.")

company_or_domain = st.text_input("Company or domain", value="perplexity.ai")
extra_urls_raw = st.text_area("Optional extra URLs (one per line)", height=80)

if st.button("🚀 Run GEO Audit", type="primary"):
    if not st.secrets.get("OPENAI_API_KEY"):
        st.error("⚠️ Add your OpenAI API key in the sidebar first!")
        st.stop()
    
    try:
        # Resolve domain
        value = company_or_domain.strip()
        if value.startswith(("http://", "https://")):
            domain_url = value
        elif "." in value:
            domain_url = "https://" + value
        else:
            st.error("Please enter a domain like 'example.com'")
            st.stop()

        urls_to_check = [domain_url]
        if extra_urls_raw.strip():
            urls_to_check.extend([line.strip() for line in extra_urls_raw.splitlines() if line.strip()])

        with st.spinner("🔍 Fetching pages..."):
            tasks = [fetch_html(u) for u in urls_to_check[:5]]  # limit to 5
            html_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        page_signals = []
        for url, html in zip(urls_to_check[:5], html_results):
            if isinstance(html, Exception):
                st.warning(f"Failed to fetch {url}")
                continue
            sig = parse_basic_page_signals(html, url)
            page_signals.append(sig)

        if not page_signals:
            st.error("Could not fetch any pages.")
            st.stop()

        # WHOIS
        ext = tldextract.extract(domain_url)
        bare_domain = f"{ext.domain}.{ext.suffix}"
        whois_info = get_domain_whois(bare_domain)

        # GEO audit
        with st.spinner("🤖 Generating GEO audit..."):
            geo_audit_text = await generate_geo_audit(
                company_name=company_or_domain,
                domain=domain_url,
                page_signals=page_signals,
                whois_info=whois_info,
            )

        # Results
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("📊 GEO Audit")
            st.markdown(geo_audit_text)
        
        with col2:
            st.subheader("📈 Page Signals")
            for p in page_signals:
                with st.expander(p["url"]):
                    st.metric("Schema blocks", p["schema_blocks_count"])
                    st.metric("Has FAQ-like", "✅" if p.get("has_faq_like_elements") else "❌")
                    st.caption(f"**Title:** {p.get('title')[:100]}...")
                    st.caption(f"**H1:** {p.get('h1')[:100]}...")

            st.subheader("🔍 Domain WHOIS")
            st.json(whois_info)

    except Exception as e:
        st.error(f"Error: {e}")
        st.exception(e)
