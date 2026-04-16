"""
utils/enricher.py
=================
Enriches journal DataFrames with Q-rank (quartile) data.

Strategy (in order of preference):
1. Local mock quartile DB (covers the most important journals).
2. Scimago live API (optional – respects rate limits).
3. Leave existing sjr_quartile value if already populated.

Usage:
    from utils.enricher import enrich_quartiles
    df = enrich_quartiles(df)
"""

from __future__ import annotations

import re
import time
import requests
import pandas as pd

# ── Mock quartile database ────────────────────────────────────────────────────
# ISSN → quartile (SJR-based).  Extend freely.
MOCK_QUARTILE_DB: dict[str, str] = {
    # Springer Nature
    "0028-0836": "Q1",  # Nature
    "1078-8956": "Q1",  # Nature Medicine
    "1087-0156": "Q1",  # Nature Biotechnology
    "1061-4036": "Q1",  # Nature Genetics
    "1465-7392": "Q1",  # Nature Cell Biology
    "2041-1723": "Q1",  # Nature Communications
    "1548-7091": "Q1",  # Nature Methods
    "2045-2322": "Q2",  # Scientific Reports
    "0950-9232": "Q1",  # Oncogene
    "1476-4598": "Q1",  # Molecular Cancer
    "1474-7596": "Q1",  # Genome Biology
    # Wiley
    "0935-9648": "Q1",  # Advanced Materials
    "1433-7851": "Q1",  # Angewandte Chemie
    "0002-7863": "Q1",  # JACS
    "0270-9139": "Q1",  # Hepatology
    "1574-7891": "Q1",  # Molecular Oncology
    "1752-4571": "Q1",  # Evolutionary Applications
    # Elsevier
    "0092-8674": "Q1",  # Cell
    "0140-6736": "Q1",  # The Lancet
    "1470-2045": "Q1",  # Lancet Oncology
    "2352-3964": "Q1",  # eBioMedicine
    "1525-0016": "Q1",  # Molecular Therapy
    "2213-2317": "Q1",  # Redox Biology
    "0304-3835": "Q1",  # Cancer Letters
    "0016-5085": "Q1",  # Gastroenterology
    "2211-1247": "Q1",  # Cell Reports
    "0022-2836": "Q1",  # JMB
    # Taylor & Francis
    "1559-2294": "Q1",  # Epigenetics
    "2162-402X": "Q1",  # Oncoimmunology
    "1949-0976": "Q1",  # Gut Microbes
    # Cambridge
    "0950-1991": "Q1",  # Development
    "0022-1120": "Q1",  # J Fluid Mechanics
    # Oxford
    "0305-1048": "Q1",  # Nucleic Acids Research
    "1467-5463": "Q1",  # Briefings in Bioinformatics
    "1873-9946": "Q1",  # J Crohn's Colitis
    "1047-3211": "Q1",  # Cerebral Cortex
    # ACS
    "1936-0851": "Q1",  # ACS Nano
    "0022-2623": "Q1",  # J Med Chem
    "1554-8929": "Q1",  # ACS Chemical Biology
    "0003-2700": "Q1",  # Analytical Chemistry
    "2161-5063": "Q1",  # ACS Synthetic Biology
    # RSC
    "2041-6520": "Q1",  # Chemical Science
    "2040-3364": "Q1",  # Nanoscale
    "1473-0197": "Q1",  # Lab on a Chip
    "1359-7345": "Q1",  # Chemical Communications
    # IOP
    "0022-3727": "Q1",  # J Physics D
    "0031-9155": "Q1",  # Physics in Medicine
    "0957-4484": "Q1",  # Nanotechnology
    "1367-2630": "Q1",  # New J Physics
}

# ── Impact factor mock data ───────────────────────────────────────────────────
MOCK_IF_DB: dict[str, float] = {
    "0028-0836": 64.8,   # Nature
    "1078-8956": 58.7,   # Nature Medicine
    "1087-0156": 46.9,   # Nature Biotechnology
    "0140-6736": 98.4,   # The Lancet
    "0092-8674": 45.5,   # Cell
    "2041-1723": 16.6,   # Nature Communications
    "0935-9648": 29.4,   # Advanced Materials
    "1433-7851": 16.6,   # Angewandte Chemie
    "0305-1048": 19.2,   # Nucleic Acids Research
    "1936-0851": 17.1,   # ACS Nano
}


def _normalise_issn(issn: str) -> str:
    """Strip hyphens and whitespace."""
    return re.sub(r"[\s\-]", "", str(issn)).strip()


def _lookup_mock(issn: str) -> str | None:
    key = _normalise_issn(issn)
    # Try with hyphen too
    formatted = f"{key[:4]}-{key[4:]}" if len(key) == 8 else key
    return (
        MOCK_QUARTILE_DB.get(formatted)
        or MOCK_QUARTILE_DB.get(key)
    )


def _lookup_scimago_live(issn: str, max_retries: int = 2) -> str | None:
    """
    Try to fetch quartile from Scimago public page.
    Returns 'Q1'/'Q2'/... or None on failure.
    Rate-limited: 1 request / 2 seconds.
    """
    clean = _normalise_issn(issn)
    url   = f"https://www.scimagojr.com/journalsearch.php?q={clean}&tip=sid&clean=0"
    try:
        for _ in range(max_retries):
            resp = requests.get(url, timeout=8, headers={"User-Agent": "Mozilla/5.0"})
            if resp.status_code == 200:
                # Very rough extraction — Scimago pages embed quartile in JSON-like blocks
                m = re.search(r"Q([1-4])", resp.text[:5000])
                if m:
                    return f"Q{m.group(1)}"
                break
            time.sleep(2)
    except Exception:
        pass
    return None


def enrich_quartiles(
    df: pd.DataFrame,
    use_live_api: bool = False,
    overwrite_existing: bool = False,
) -> pd.DataFrame:
    """
    Add / update the ``sjr_quartile`` column in *df*.

    Parameters
    ----------
    df                : Journal DataFrame (must have 'issn' and 'sjr_quartile').
    use_live_api      : If True, attempt Scimago live lookup for unresolved rows.
    overwrite_existing: If True, re-lookup even rows that already have a quartile.

    Returns
    -------
    Updated DataFrame.
    """
    if "sjr_quartile" not in df.columns:
        df["sjr_quartile"] = ""
    if "issn" not in df.columns:
        return df

    df = df.copy()

    for idx, row in df.iterrows():
        # Skip if already filled and not overwriting
        current = str(row.get("sjr_quartile", "")).strip()
        if current and current not in ("", "nan", "Unknown") and not overwrite_existing:
            continue

        issn = str(row.get("issn", "")).strip()
        if not issn or issn in ("", "nan"):
            continue

        # 1. Mock lookup
        quartile = _lookup_mock(issn)

        # 2. Live Scimago (optional, slow)
        if quartile is None and use_live_api:
            quartile = _lookup_scimago_live(issn)
            time.sleep(1.5)   # be polite

        if quartile:
            df.at[idx, "sjr_quartile"] = quartile

    return df


def enrich_impact_factors(df: pd.DataFrame) -> pd.DataFrame:
    """Fill in missing impact_factor values from mock DB."""
    if "impact_factor" not in df.columns:
        df["impact_factor"] = ""
    if "issn" not in df.columns:
        return df

    df = df.copy()
    for idx, row in df.iterrows():
        if str(row.get("impact_factor", "")).strip() in ("", "nan"):
            issn = str(row.get("issn", "")).strip()
            val  = MOCK_IF_DB.get(issn) or MOCK_IF_DB.get(_normalise_issn(issn))
            if val:
                df.at[idx, "impact_factor"] = str(val)
    return df
