"""
pages/1_📚_Publisher_Detail.py
================================
Streamlit multi-page app — Browse journals for a single publisher,
with sorting, filtering, and per-journal detail expansion.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import streamlit as st
from backend.data_loader import load_publishers, load_local_csv

st.set_page_config(
    page_title="Yayıncı Detayı | OA Journal Finder",
    page_icon="📚",
    layout="wide",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
</style>
""", unsafe_allow_html=True)

# ── Load publisher list ───────────────────────────────────────────────────────
publishers = load_publishers()
pub_map    = {p["name"]: p for p in publishers}

st.title("📚 Yayıncı Dergi Listesi")
st.caption("Bir yayıncı seçin, tüm fonlanan OA dergilerini filtreleyin ve keşfedin.")

# ── Selector ─────────────────────────────────────────────────────────────────
pub_name = st.selectbox(
    "Yayıncı Seçin",
    options=[p["name"] for p in publishers],
    index=0,
)
pub = pub_map[pub_name]

# ── Load data ─────────────────────────────────────────────────────────────────
@st.cache_data(show_spinner="Dergi listesi yükleniyor…")
def _load(pub_id: str, pub_name: str) -> pd.DataFrame:
    return load_local_csv(pub_id, pub_name)

df = _load(pub["id"], pub["name"])

if df.empty:
    st.warning("Bu yayıncı için yerel veri dosyası bulunamadı.")
    st.stop()

# ── Sidebar filters ───────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"### 🏢 {pub['name']}")
    st.markdown(f"**Anlaşma:** {pub.get('agreement_period','—')}")
    st.markdown(f"**Kota:** {pub.get('quota') or '—'}")
    st.markdown(f"**OA Sayfası:** [Ziyaret Et]({pub.get('oa_url','#')})")
    st.markdown("---")
    st.markdown("### Filtrele")

    # Quartile filter
    available_quartiles = sorted(df["sjr_quartile"].dropna().unique().tolist())
    selected_q = st.multiselect(
        "Kuartil",
        options=available_quartiles,
        default=[q for q in available_quartiles if "Q1" in q],
    )

    # Subject area filter
    available_subjects = sorted(df["subject_area"].dropna().unique().tolist())
    selected_subjects  = st.multiselect("Konu Alanı", options=available_subjects)

    # OA type filter
    if "oa_type" in df.columns:
        oa_types = sorted(df["oa_type"].dropna().unique().tolist())
        selected_oa = st.multiselect("OA Türü", options=oa_types)
    else:
        selected_oa = []

    # Text search
    text_search = st.text_input("🔍 Dergi adında ara…", placeholder="nature, cancer, …")

# ── Apply filters ─────────────────────────────────────────────────────────────
filtered = df.copy()
if selected_q:
    filtered = filtered[filtered["sjr_quartile"].isin(selected_q)]
if selected_subjects:
    filtered = filtered[filtered["subject_area"].isin(selected_subjects)]
if selected_oa:
    filtered = filtered[filtered["oa_type"].isin(selected_oa)]
if text_search:
    filtered = filtered[
        filtered["journal_title"].str.contains(text_search, case=False, na=False)
    ]

filtered = filtered.reset_index(drop=True)

# ── Stats row ─────────────────────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
c1.metric("Toplam Dergi",   len(df))
c2.metric("Filtrelenmiş",   len(filtered))
c3.metric("Q1 Sayısı",      (df["sjr_quartile"].str.upper().str.contains("Q1", na=False)).sum())
c4.metric("Konu Alanı",     df["subject_area"].nunique())

st.markdown("---")

# ── Table + detail expansion ──────────────────────────────────────────────────
if filtered.empty:
    st.info("Filtre kriterlerinize uyan dergi bulunamadı.")
else:
    # Sortable columns
    sort_col = st.selectbox(
        "Sıralama Kriteri",
        ["journal_title", "sjr_quartile", "impact_factor", "sjr_score", "h_index"],
        format_func=lambda x: {
            "journal_title": "Dergi Adı", "sjr_quartile": "Kuartil",
            "impact_factor": "Etki Faktörü", "sjr_score": "SJR Skoru", "h_index": "H-indeks",
        }.get(x, x),
    )

    ascending = st.toggle("Artan Sıra", value=True)
    try:
        filtered = filtered.sort_values(sort_col, ascending=ascending)
    except Exception:
        pass

    # Render expandable journal rows
    for _, row in filtered.iterrows():
        quartile = str(row.get("sjr_quartile", "—"))
        q_color  = "#276749" if "Q1" in quartile.upper() else ("#744210" if "Q2" in quartile.upper() else "#553c9a")
        q_bg     = "#c6f6d5" if "Q1" in quartile.upper() else ("#feebc8" if "Q2" in quartile.upper() else "#e9d8fd")

        with st.expander(
            f"**{row.get('journal_title','—')}**  •  "
            f"{quartile}  •  {row.get('subject_area','—')}"
        ):
            cols = st.columns([2, 1, 1, 1, 1])
            cols[0].markdown(f"**Yayıncı:** {row.get('publisher','—')}")
            cols[1].markdown(f"**ISSN:** `{row.get('issn','—')}`")
            cols[2].markdown(f"**E-ISSN:** `{row.get('eissn','—')}`")
            cols[3].markdown(f"**IF:** `{row.get('impact_factor','—')}`")
            cols[4].markdown(f"**SJR:** `{row.get('sjr_score','—')}`")

            st.markdown(f"**OA Türü:** {row.get('oa_type','—')}  |  **H-indeks:** {row.get('h_index','—')}")

            scope = str(row.get("scope", "")).strip()
            if scope:
                st.markdown("**Kapsam:**")
                st.markdown(f"> {scope[:500]}{'…' if len(scope)>500 else ''}")

    # Download
    st.markdown("---")
    dl_df = filtered[
        [c for c in ["journal_title","issn","eissn","subject_area","sjr_quartile",
                     "impact_factor","sjr_score","oa_type","h_index"] if c in filtered.columns]
    ]
    st.download_button(
        "⬇️ Filtrelenmiş Listeyi İndir (CSV)",
        data=dl_df.to_csv(index=False).encode("utf-8"),
        file_name=f"{pub['id']}_oa_journals.csv",
        mime="text/csv",
        use_container_width=True,
    )
