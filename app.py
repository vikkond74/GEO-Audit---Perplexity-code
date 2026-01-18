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
                results = await asyncio.gather(*[client.get(u) for u in urls], return_exceptions=T
