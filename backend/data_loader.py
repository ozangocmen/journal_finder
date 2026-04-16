"""
data_loader.py
==============
Loads publisher journal lists from local CSV / Excel files.
Also supports downloading directly from a remote URL (e.g., the Ege Ü library page).
"""

import os
import json
import pandas as pd
import requests
from io import BytesIO
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR   = Path(__file__).resolve().parent.parent
DATA_DIR   = BASE_DIR / "data"
PUB_FILE   = DATA_DIR / "publishers.json"

# Required columns every loaded DataFrame must expose
REQUIRED_COLS = [
    "journal_title",
    "subject_area",
    "publisher",
    "sjr_quartile",
    "scope",
]

# Column-name aliases: maps common column variants → canonical name
COL_ALIASES: dict[str, str] = {
    # title
    "journal name": "journal_title",
    "journal": "journal_title",
    "title": "journal_title",
    "name": "journal_title",
    "dergi adı": "journal_title",
    "dergi": "journal_title",
    # issn
    "print issn": "issn",
    "p-issn": "issn",
    # eissn
    "online issn": "eissn",
    "e-issn": "eissn",
    # subject
    "subject": "subject_area",
    "category": "subject_category",
    "discipline": "subject_area",
    # quartile
    "quartile": "sjr_quartile",
    "q": "sjr_quartile",
    "sjr quartile": "sjr_quartile",
    # impact factor
    "if": "impact_factor",
    "jif": "impact_factor",
    "impact factor": "impact_factor",
    # scope / aims
    "aims and scope": "scope",
    "aims & scope": "scope",
    "description": "scope",
    "abstract": "scope",
}


def load_publishers() -> list[dict]:
    """Return the list of publisher metadata dicts from publishers.json."""
    with open(PUB_FILE, encoding="utf-8") as fh:
        return json.load(fh)


def _normalise_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Lowercase + strip column names, apply aliases."""
    df.columns = [c.strip().lower() for c in df.columns]
    df = df.rename(columns=COL_ALIASES)
    return df


def _ensure_required_cols(df: pd.DataFrame, publisher_name: str) -> pd.DataFrame:
    """Add missing required columns with sensible defaults."""
    if "journal_title" not in df.columns:
        # Try to find anything that could be a title
        for col in df.columns:
            if "title" in col or "journal" in col or "name" in col:
                df = df.rename(columns={col: "journal_title"})
                break
        else:
            df["journal_title"] = "Unknown"

    if "publisher" not in df.columns:
        df["publisher"] = publisher_name

    if "sjr_quartile" not in df.columns:
        df["sjr_quartile"] = "Unknown"

    if "scope" not in df.columns:
        # Build a minimal scope from title + subject if available
        parts = [df.get("journal_title", pd.Series(dtype=str))]
        if "subject_area" in df.columns:
            parts.append(df["subject_area"])
        if "subject_category" in df.columns:
            parts.append(df["subject_category"])
        df["scope"] = pd.concat(parts, axis=1).fillna("").agg(" ".join, axis=1)

    if "subject_area" not in df.columns:
        df["subject_area"] = "General"

    for col in ["issn", "eissn", "impact_factor", "h_index", "subject_category", "oa_type", "sjr_score"]:
        if col not in df.columns:
            df[col] = ""

    return df


def load_local_csv(publisher_id: str, publisher_name: str) -> pd.DataFrame:
    """
    Load the CSV / Excel file for *publisher_id* from the data directory.
    Returns a normalised DataFrame.
    """
    # Try extensions in order of preference
    for ext in (".csv", ".xlsx", ".xls"):
        fpath = DATA_DIR / f"{publisher_id}{ext}"
        if fpath.exists():
            if ext == ".csv":
                df = pd.read_csv(fpath, dtype=str)
            else:
                df = pd.read_excel(fpath, dtype=str)
            df = _normalise_columns(df)
            df = _ensure_required_cols(df, publisher_name)
            df = df.fillna("")
            return df

    # Return empty DataFrame if no file found
    return _ensure_required_cols(pd.DataFrame(), publisher_name)


def load_from_url(url: str, publisher_name: str, file_type: str = "auto") -> pd.DataFrame:
    """
    Download and parse a remote journal list file.
    *file_type* can be 'csv', 'xlsx', or 'auto' (guessed from URL).
    """
    try:
        resp = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        raw = BytesIO(resp.content)

        if file_type == "auto":
            low = url.lower()
            file_type = "xlsx" if (".xlsx" in low or ".xls" in low) else "csv"

        if file_type == "xlsx":
            df = pd.read_excel(raw, dtype=str)
        else:
            df = pd.read_csv(raw, dtype=str)

        df = _normalise_columns(df)
        df = _ensure_required_cols(df, publisher_name)
        df = df.fillna("")
        return df

    except Exception as exc:
        print(f"[data_loader] Could not fetch {url}: {exc}")
        return _ensure_required_cols(pd.DataFrame(), publisher_name)


def load_uploaded_file(uploaded_file, publisher_name: str) -> pd.DataFrame:
    """
    Parse a Streamlit UploadedFile object (CSV or Excel).
    Returns a normalised DataFrame.
    """
    fname = uploaded_file.name.lower()
    if fname.endswith(".csv"):
        df = pd.read_csv(uploaded_file, dtype=str)
    else:
        df = pd.read_excel(uploaded_file, dtype=str)

    df = _normalise_columns(df)
    df = _ensure_required_cols(df, publisher_name)
    df = df.fillna("")
    return df


def load_all_publishers() -> pd.DataFrame:
    """
    Convenience helper: load every publisher's local CSV and return one
    combined DataFrame with a 'publisher_id' column added.
    """
    publishers = load_publishers()
    frames: list[pd.DataFrame] = []
    for pub in publishers:
        df = load_local_csv(pub["id"], pub["name"])
        if not df.empty:
            df["publisher_id"] = pub["id"]
            frames.append(df)
    if frames:
        return pd.concat(frames, ignore_index=True)
    return pd.DataFrame()
