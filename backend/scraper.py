"""
scraper.py
==========
Fetches the actual Open Access journal Excel/CSV list files
from publisher agreement pages of Ege University Library.

Maps each publisher_id → direct Excel download URL (if known).
Falls back gracefully to local CSV files when a URL is not available
or the download fails.
"""

from __future__ import annotations

import re
import requests
from bs4 import BeautifulSoup  # type: ignore  (optional dep)
from pathlib import Path

# ── Known direct download URLs ──────────────────────────────────────────────
# These are populated from the actual library pages.
DIRECT_URLS: dict[str, str] = {
    "springer_nature": (
        "https://kutuphane.ege.edu.tr/files/kutuphane/icerik/"
        "sn_26_ae_dergi_listesi-v4 (1).xlsx"
    ),
    # Add others here as you discover them from the library pages:
    # "wiley": "https://...",
    # "elsevier": "https://...",
}

# ── Page URLs to scrape for Excel links ─────────────────────────────────────
PAGE_URLS: dict[str, str] = {
    "springer_nature": "https://kutuphane.ege.edu.tr/tr-18950/springnature.html",
    "wiley":           "https://kutuphane.ege.edu.tr/tr-17401/read_publish_modeline_gecis.html",
    "cambridge":       "https://kutuphane.ege.edu.tr/tr-15765/cambridge_university_press_journal_(cup).html",
    "oxford":          "https://kutuphane.ege.edu.tr/tr-19068/oxford.html",
    "acs":             "https://kutuphane.ege.edu.tr/tr-15763/american_chmeical_society_(acs).html",
    "rsc":             "https://kutuphane.ege.edu.tr/tr-23741/royal_society_of_chemistry_(rsc).html",
    "sage":            "https://kutuphane.ege.edu.tr/tr-21179/sage_premier.html",
    "iop":             "https://kutuphane.ege.edu.tr/tr-21178/iop_(institute_of_physics).html",
}

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; OAJournalFinder/1.0)"}
BASE_URL = "https://kutuphane.ege.edu.tr"


def _find_excel_link_on_page(page_url: str) -> str | None:
    """
    Download *page_url* and return the first href that points to
    an Excel (.xlsx / .xls) or CSV file.
    """
    try:
        resp = requests.get(page_url, timeout=15, headers=HEADERS)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup.find_all("a", href=True):
            href: str = tag["href"]
            if re.search(r"\.(xlsx?|csv)(\?.*)?$", href, re.IGNORECASE):
                if href.startswith("http"):
                    return href
                return BASE_URL + ("/" if not href.startswith("/") else "") + href
    except Exception as exc:
        print(f"[scraper] Could not scrape {page_url}: {exc}")
    return None


def get_download_url(publisher_id: str) -> str | None:
    """
    Return the best download URL for *publisher_id*.

    Priority
    --------
    1. Hardcoded DIRECT_URLS
    2. Scraped link from the publisher page
    3. None → caller should fall back to local CSV
    """
    if publisher_id in DIRECT_URLS:
        return DIRECT_URLS[publisher_id]

    page_url = PAGE_URLS.get(publisher_id)
    if page_url:
        return _find_excel_link_on_page(page_url)

    return None
