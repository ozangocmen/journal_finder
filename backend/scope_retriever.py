import json
import logging
import time
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

CACHE_FILE = Path(__file__).parent.parent / "data" / "scope_cache.json"

@dataclass
class ScopeResult:
    text: str
    source_url: str
    retrieval_status: str  # "SUCCESS", "RETRIEVAL ERROR", "CACHED"
    timestamp: float

def load_cache() -> dict:
    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading scope cache: {e}")
    return {}

def save_cache(cache: dict):
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Error saving scope cache: {e}")

# Global cache
SCOPE_CACHE = load_cache()
CACHE_TTL = 30 * 24 * 3600  # 30 days

def resolve_url(journal_title: str, publisher: str, issn: str, eissn: str = "") -> Optional[str]:
    """Resolves canonical URL for journal Aims & Scope page based on publisher."""
    publisher_lower = publisher.lower().replace(" ", "")
    
    clean_issn = str(issn).strip().replace("-", "") if pd.isna(issn) == False else ""
    clean_eissn = str(eissn).strip().replace("-", "") if pd.isna(eissn) == False else ""
    target_issn = clean_eissn if clean_eissn else clean_issn
    formatted_issn = f"{target_issn[:4]}-{target_issn[4:]}" if len(target_issn) == 8 else target_issn

    slug = re.sub(r"[^a-z0-9]+", "-", journal_title.lower()).strip("-")

    if "springer" in publisher_lower:
        if formatted_issn:
            return f"https://link.springer.com/journal/{formatted_issn}/aims-and-scope"
    elif "wiley" in publisher_lower:
        if target_issn:
            return f"https://onlinelibrary.wiley.com/journal/{target_issn}"
    elif "elsevier" in publisher_lower:
        return f"https://www.sciencedirect.com/journal/{slug}/about/aims-and-scope"
    elif "oxford" in publisher_lower:
        return f"https://academic.oup.com/{slug}/pages/About"
    elif "cambridge" in publisher_lower:
        return f"https://www.cambridge.org/core/journals/{slug}/information/aims-scope"
    
    # Generic Google search fallback could go here, but omitted to prevent errors
    return None

import pandas as pd

def fetch_and_parse(url: str) -> str:
    """Fetches URL and extracts main text content."""
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        
        # Remove unwanted elements
        for tag in soup(["nav", "footer", "script", "style", "header", "aside"]):
            tag.decompose()
            
        text = soup.get_text(separator=' ', strip=True)
        # Basic heuristic to find "Aims and Scope" or simply take top content
        aims_idx = text.lower().find("aims and scope")
        if aims_idx != -1 and aims_idx < len(text) - 50:
            text = text[aims_idx:aims_idx+3000]
        else:
            text = text[:3000] # Just grab first 3k chars if no marker
            
        return text.strip()
    except Exception as e:
        logger.warning(f"Failed to fetch {url}: {e}")
        return ""

def retrieve_scope(journal_title: str, publisher: str, issn: str, eissn: str = "") -> ScopeResult:
    """Retrieves Aims & Scope with caching."""
    cache_key = f"{publisher}_{journal_title}_{issn}".lower()
    
    now = time.time()
    
    if cache_key in SCOPE_CACHE:
        cached = SCOPE_CACHE[cache_key]
        if now - cached.get("timestamp", 0) < CACHE_TTL:
            return ScopeResult(
                text=cached["text"],
                source_url=cached.get("url", ""),
                retrieval_status="CACHED",
                timestamp=cached["timestamp"]
            )
            
    url = resolve_url(journal_title, publisher, issn, eissn)
    
    if not url:
        return ScopeResult(text="", source_url="", retrieval_status="RETRIEVAL ERROR", timestamp=now)
        
    text = fetch_and_parse(url)
    
    status = "SUCCESS" if text else "RETRIEVAL ERROR"
    
    if status == "SUCCESS":
        SCOPE_CACHE[cache_key] = {
            "text": text,
            "url": url,
            "timestamp": now
        }
        # Save cache every few updates ideally, but we'll do it on success here
        save_cache(SCOPE_CACHE)
        
    return ScopeResult(text=text, source_url=url, retrieval_status=status, timestamp=now)
