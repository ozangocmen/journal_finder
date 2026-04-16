"""
app.py  —  OA Journal Finder
===========================================
Streamlit application for finding the best Open Access journals
for a researcher's article, based on funded Read & Publish agreements.

Run with:
    streamlit run app.py
"""

from __future__ import annotations

import os
import sys
import time
import pandas as pd
import streamlit as st
from pathlib import Path

# ── Path setup ────────────────────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent))
from backend.data_loader import load_publishers, load_local_csv, load_uploaded_file, load_all_publishers
from backend.matcher import RAGMatcher
import frontend.components as fc

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="OA Journal Finder | Ege Üniversitesi",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS Theme ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* ── Root & Font ──────────────────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

/* ── App background ─────────────────────────────────────────────*/
.main .block-container {
    padding-top: 1.5rem;
    padding-bottom: 3rem;
    max-width: 1280px;
}

/* ── Header hero ─────────────────────────────────────────────── */
.hero {
    background: linear-gradient(135deg, #0f172a 0%, #1e3a5f 60%, #0e4d6e 100%);
    border-radius: 16px;
    padding: 2.5rem 3rem;
    color: white;
    margin-bottom: 2rem;
    box-shadow: 0 8px 32px rgba(0,0,0,0.18);
    position: relative;
    overflow: hidden;
}
.hero::before {
    content: "";
    position: absolute;
    top: -60px; right: -60px;
    width: 220px; height: 220px;
    border-radius: 50%;
    background: rgba(255,255,255,0.05);
}
.hero h1 { font-size: 2rem; font-weight: 700; margin: 0 0 .4rem; }
.hero p  { font-size: 1.05rem; opacity: .85; margin: 0; }
.hero .badge {
    display: inline-block;
    background: rgba(255,255,255,0.15);
    border: 1px solid rgba(255,255,255,0.25);
    border-radius: 100px;
    padding: 4px 14px;
    font-size: .78rem;
    margin-top: .9rem;
    margin-right: .4rem;
}

/* ── Publisher cards ─────────────────────────────────────────── */
.pub-card {
    background: white;
    border-radius: 14px;
    padding: 1.3rem 1.1rem 1rem;
    border: 2px solid #e8edf2;
    text-align: center;
    cursor: pointer;
    transition: all .22s ease;
    height: 100%;
    position: relative;
    overflow: hidden;
}
.pub-card:hover {
    transform: translateY(-4px);
    box-shadow: 0 12px 28px rgba(0,0,0,0.10);
    border-color: var(--pub-color);
}
.pub-card.selected {
    border-color: var(--pub-color);
    background: var(--pub-bg);
    box-shadow: 0 8px 24px rgba(0,0,0,0.10);
}
.pub-logo {
    width: 54px; height: 54px;
    border-radius: 12px;
    display: flex; align-items: center; justify-content: center;
    font-size: 1.1rem; font-weight: 800; color: white;
    margin: 0 auto .75rem;
}
.pub-name  { font-weight: 700; font-size: .95rem; color: #1a202c; margin-bottom: .25rem; }
.pub-count { font-size: .78rem; color: #718096; }
.pub-badge-active {
    position: absolute; top: 10px; right: 10px;
    background: #38a169; color: white;
    border-radius: 100px; font-size: .65rem; padding: 2px 8px; font-weight: 600;
}

/* ── Section headings ────────────────────────────────────────── */
.section-head {
    font-size: 1.15rem; font-weight: 700; color: #1a202c;
    margin: 2rem 0 1rem;
    display: flex; align-items: center; gap: .5rem;
}

/* ── Query box ───────────────────────────────────────────────── */
.stTextArea > div > div > textarea {
    border-radius: 10px !important;
    border: 2px solid #e2e8f0 !important;
    font-size: .95rem !important;
    padding: .8rem 1rem !important;
}
.stTextArea > div > div > textarea:focus {
    border-color: #3182ce !important;
    box-shadow: 0 0 0 3px rgba(49,130,206,.15) !important;
}

/* ── Result card ─────────────────────────────────────────────── */
.result-card {
    background: white;
    border-radius: 12px;
    padding: 1.2rem 1.4rem;
    border: 1.5px solid #e8edf2;
    margin-bottom: .9rem;
    transition: box-shadow .2s;
}
.result-card:hover { box-shadow: 0 6px 20px rgba(0,0,0,0.08); }
.result-rank {
    display: inline-flex; align-items: center; justify-content: center;
    width: 32px; height: 32px; border-radius: 8px;
    font-weight: 800; font-size: .9rem; color: white;
    margin-right: .7rem;
}
.result-title { font-weight: 700; font-size: 1rem; color: #1a202c; }
.result-meta  { font-size: .8rem; color: #718096; margin-top: .2rem; }
.score-bar-outer {
    background: #edf2f7; border-radius: 100px;
    height: 8px; width: 100%; margin-top: .5rem;
}
.score-bar-inner {
    height: 8px; border-radius: 100px;
    background: linear-gradient(90deg, #3182ce, #63b3ed);
}
.pill {
    display: inline-block;
    border-radius: 100px;
    padding: 2px 10px;
    font-size: .72rem;
    font-weight: 600;
    margin-right: 4px;
}
.pill-q1  { background: #c6f6d5; color: #276749; }
.pill-oa  { background: #bee3f8; color: #2b6cb0; }
.pill-pub { background: #feebc8; color: #7b341e; }
.pill-sub { background: #e9d8fd; color: #553c9a; }

/* ── Metric boxes ────────────────────────────────────────────── */
.metric-box {
    background: white; border-radius: 12px;
    padding: 1.1rem 1.4rem;
    border: 1.5px solid #e8edf2;
    text-align: center;
}
.metric-value { font-size: 1.8rem; font-weight: 800; color: #2d3748; }
.metric-label { font-size: .8rem; color: #718096; margin-top: .1rem; }

/* ── Empty state ─────────────────────────────────────────────── */
.empty-state {
    text-align: center; padding: 3rem 1rem; color: #a0aec0;
    background: #f7fafc; border-radius: 12px; border: 2px dashed #e2e8f0;
}
.empty-state .icon { font-size: 3rem; }
.empty-state p { margin-top: .5rem; font-size: .95rem; }

/* ── Sidebar ─────────────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background: #f0f4f8;
}
[data-testid="stSidebar"] hr { border-color: #e2e8f0; }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# Session state initialisation
# ══════════════════════════════════════════════════════════════════════════════
if "selected_publishers" not in st.session_state:
    st.session_state.selected_publishers: set[str] = set()
if "combined_df" not in st.session_state:
    st.session_state.combined_df: pd.DataFrame | None = None
if "matcher" not in st.session_state:
    st.session_state.matcher: RAGMatcher | None = None
if "analysis_result" not in st.session_state:
    st.session_state.analysis_result = None
if "last_query" not in st.session_state:
    st.session_state.last_query: str = ""


# ══════════════════════════════════════════════════════════════════════════════
# Data helpers (cached)
# ══════════════════════════════════════════════════════════════════════════════
@st.cache_data(show_spinner=False)
def get_publishers() -> list[dict]:
    return load_publishers()


@st.cache_data(show_spinner=False)
def get_publisher_df(publisher_id: str, publisher_name: str) -> pd.DataFrame:
    return load_local_csv(publisher_id, publisher_name)


@st.cache_data(show_spinner=False)
def get_all_df() -> pd.DataFrame:
    return load_all_publishers()


def build_matcher(df: pd.DataFrame, api_key: str = "") -> RAGMatcher:
    return RAGMatcher(df, api_key)


# ══════════════════════════════════════════════════════════════════════════════
# Sidebar
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.image(
        "https://www.ege.edu.tr/img/ege-univ-logo.png",
        width=160,
    )
    st.markdown("### ⚙️ Ayarlar / Settings")
    st.markdown("---")

    # Q1 filter
    q1_only = st.toggle("🏆 Yalnızca Q1 dergileri göster", value=True)

    # Score threshold
    min_score = st.slider("Minimum Eşleşme Skoru (%)", 0, 50, 5) / 100

    # Top-k
    top_k = st.slider("Maksimum Sonuç Sayısı", 5, 50, 20)

    st.markdown("---")
    st.markdown("### 📤 Kendi CSV/Excel Dosyanı Yükle")
    st.caption("Kütüphanenizin yayıncı anlaşma dosyasını buraya yükleyin.")
    uploaded = st.file_uploader(
        "Dosya seç (.csv veya .xlsx)",
        type=["csv", "xlsx", "xls"],
        label_visibility="collapsed",
    )

    st.markdown("---")
    st.markdown("### 🔑 Claude API Key")
    st.caption("Gerekli: Tam CAS analizi ve RAG Retrieval için Anthropic API Key gereklidir. Yoksa TF-IDF varsayılanı çalışır.")
    api_key = st.text_input("Anthropic API Key", type="password", placeholder="sk-ant-…")
    
    # Store api key in session to rebuild matcher if it changes
    if "api_key" not in st.session_state:
        st.session_state.api_key = api_key
    elif st.session_state.api_key != api_key:
        st.session_state.api_key = api_key
        st.session_state.combined_df = None # force rebuild

    st.markdown("---")
    st.markdown(
        "<small>🔬 <b>Ege Üniversitesi</b> Kütüphane & Dokümantasyon<br>"
        "Oku & Yayımla Anlaşmaları Portalı — v1.0</small>",
        unsafe_allow_html=True,
    )


# ══════════════════════════════════════════════════════════════════════════════
# Hero Header
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div class="hero">
  <h1>🔬 Academic Publishing Assistant v2.0</h1>
  <p>RAG-Powered Journal Recommendation Engine for precision semantic matching.</p>
  <span class="badge">📚 12 Yayıncı</span>
  <span class="badge">🏆 Q1 Filtreli</span>
  <span class="badge">🤖 RAG & Claude API CAS Eşleştirme</span>
  <span class="badge">🆓 APC Ücretsiz</span>
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# Publisher Dashboard
# ══════════════════════════════════════════════════════════════════════════════
publishers = get_publishers()

st.markdown('<div class="section-head">🏢 Yayıncı Seçimi — Hangi Anlaşmaları Dahil Etmek İstiyorsunuz?</div>', unsafe_allow_html=True)
st.caption("Bir veya daha fazla yayıncıya tıklayarak seçin. Seçili olanlar mavi kenarlıkla gösterilir.")

# Select-all / clear buttons
c1, c2, _ = st.columns([1, 1, 8])
with c1:
    if st.button("✅ Tümünü Seç", use_container_width=True):
        st.session_state.selected_publishers = {p["id"] for p in publishers}
        st.session_state.combined_df = None
        st.session_state.matcher     = None
with c2:
    if st.button("❌ Temizle", use_container_width=True):
        st.session_state.selected_publishers = set()
        st.session_state.combined_df = None
        st.session_state.matcher     = None

# Publisher grid — 5 cards per row
cols = st.columns(6)
for i, pub in enumerate(publishers):
    col = cols[i % 6]
    is_selected = pub["id"] in st.session_state.selected_publishers

    with col:
        # Build card HTML
        selected_cls = "selected" if is_selected else ""
        card_html = f"""
        <div class="pub-card {selected_cls}"
             style="--pub-color:{pub['color']}; --pub-bg:{pub['bg_color']}">
          <div class="pub-logo" style="background:{pub['color']}">{pub['short']}</div>
          <div class="pub-name">{pub['name']}</div>
          <div class="pub-count">~{pub['journal_count']:,} dergi</div>
          <div class="pub-badge-active">✓ Aktif</div>
        </div>
        """
        st.markdown(card_html, unsafe_allow_html=True)

        # Toggle button below card
        btn_label = "✓ Seçili" if is_selected else "Seç"
        btn_type  = "primary" if is_selected else "secondary"
        if st.button(btn_label, key=f"pub_{pub['id']}", use_container_width=True, type=btn_type):
            if pub["id"] in st.session_state.selected_publishers:
                st.session_state.selected_publishers.discard(pub["id"])
            else:
                st.session_state.selected_publishers.add(pub["id"])
            # Invalidate cached data
            st.session_state.combined_df = None
            st.session_state.matcher     = None
            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# Load / rebuild index whenever selection changes
# ══════════════════════════════════════════════════════════════════════════════
def _rebuild_index():
    selected = st.session_state.selected_publishers
    if not selected:
        st.session_state.combined_df = None
        st.session_state.matcher     = None
        return

    frames: list[pd.DataFrame] = []

    # If user uploaded a file, load it too
    if uploaded is not None:
        udf = load_uploaded_file(uploaded, "Uploaded File")
        udf["publisher_id"] = "__upload__"
        frames.append(udf)

    for pub in publishers:
        if pub["id"] in selected:
            df = get_publisher_df(pub["id"], pub["name"])
            if not df.empty:
                df["publisher_id"] = pub["id"]
                frames.append(df)

    if frames:
        combined = pd.concat(frames, ignore_index=True).fillna("")
        st.session_state.combined_df = combined
        with st.spinner("🔧 Dergi indeksi oluşturuluyor…"):
            st.session_state.matcher = build_matcher(combined, st.session_state.get("api_key", ""))
    else:
        st.session_state.combined_df = None
        st.session_state.matcher     = None


# Rebuild whenever selection changes or upload appears
if st.session_state.combined_df is None and st.session_state.selected_publishers:
    _rebuild_index()


# ══════════════════════════════════════════════════════════════════════════════
# Stats bar
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.combined_df is not None:
    df_all = st.session_state.combined_df
    n_total = len(df_all)
    n_q1    = (df_all["sjr_quartile"].str.upper().str.contains("Q1", na=False)).sum()
    n_pubs  = df_all["publisher_id"].nunique()
    n_areas = df_all["subject_area"].nunique()

    st.markdown("---")
    m1, m2, m3, m4 = st.columns(4)
    for col_w, val, label, icon in [
        (m1, n_total, "Toplam Dergi",       "📚"),
        (m2, n_q1,    "Q1 Dergi",           "🏆"),
        (m3, n_pubs,  "Seçili Yayıncı",     "🏢"),
        (m4, n_areas, "Konu Alanı",         "🔖"),
    ]:
        with col_w:
            st.markdown(
                f'<div class="metric-box">'
                f'<div class="metric-value">{icon} {val:,}</div>'
                f'<div class="metric-label">{label}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )


# ══════════════════════════════════════════════════════════════════════════════
# Search / Matching form
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-head">🔍 Makale Eşleştirme</div>', unsafe_allow_html=True)

if not st.session_state.selected_publishers:
    st.markdown("""
    <div class="empty-state">
      <div class="icon">☝️</div>
      <p>Lütfen önce en az bir <strong>yayıncı seçin</strong>.</p>
    </div>
    """, unsafe_allow_html=True)
else:
    with st.form("search_form", clear_on_submit=False):
        query = st.text_area(
            "📝 Makale başlığı, anahtar kelimeler veya özet",
            height=130,
            placeholder=(
                "Örnek: CLDN4 and CLDN7 claudin expression in colorectal cancer using single-cell "
                "transcriptomics and spatial genomics. Keywords: tight junction, epithelial barrier, "
                "tumour microenvironment, scRNA-seq."
            ),
        )
        sub_filter = st.text_input(
            "🔖 Konu alanı filtresi (isteğe bağlı)",
            placeholder="Örnek: Oncology, Genetics, Cell Biology",
        )
        search_btn = st.form_submit_button(
            "🚀 En Uygun Dergileri Bul",
            use_container_width=True,
            type="primary",
        )

    if search_btn and query.strip():
        if st.session_state.matcher is None:
            st.warning("Lütfen önce en az bir yayıncı seçin.")
        else:
            with st.spinner("🤖 RAG Pipeline çalışıyor (Bu işlem 30-60 sn sürebilir)…"):
                st.session_state.matcher.api_key = api_key # update key if changed
                
                result = st.session_state.matcher.analyze(
                    manuscript_text=query,
                    top_k=top_k,
                    q1_only=q1_only
                )

                st.session_state.analysis_result = result
                st.session_state.last_query  = query


# ══════════════════════════════════════════════════════════════════════════════
# Results
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.analysis_result is not None:
    res_obj = st.session_state.analysis_result
    res = res_obj.shortlist
    q   = st.session_state.last_query
    
    st.markdown("---")
    fc.render_fingerprint(res_obj.fingerprint)
    st.markdown("---")
    st.markdown(
        f'<div class="section-head">📊 Sonuçlar — '
        f'{len(res)} Dergi Bulundu</div>',
        unsafe_allow_html=True,
    )

    if res.empty:
        st.markdown("""
        <div class="empty-state">
          <div class="icon">🔍</div>
          <p>Arama kriterlerinize uyan Q1 dergisi bulunamadı.<br>
          Konu filtresini kaldırmayı veya farklı anahtar kelimeler denemeyi deneyin.</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        # ── Tab layout ────────────────────────────────────────────────────────
        tab_cards, tab_table, tab_chart = st.tabs([
            "🃏 Kart Görünümü",
            "📋 Tablo Görünümü",
            "📈 Analiz",
        ])

        # ── Publisher colour map ──────────────────────────────────────────────
        pub_colors = {p["id"]: p["color"] for p in publishers}

        # ── KART GÖRÜNÜMÜ ─────────────────────────────────────────────────────
        with tab_cards:
            for rank, (_, row) in enumerate(res.iterrows(), start=1):
                pub_id   = row.get("publisher_id", "")
                color    = pub_colors.get(pub_id, "#3182ce")
                risk     = res_obj.risks.get(row.get('journal_title'), None)
                
                fc.render_journal_card(rank, row, risk, color)
            
            fc.render_borderline_list(res_obj.borderline)
            
            st.markdown("### 📝 Methodological Notes & Caveats")
            st.markdown("- Metrics sourced from JCR/Scopus where available, fallback to mock DB otherwise.")
            unsuccessful = res[res['scope_retrieval_status'] != 'SUCCESS']
            if not unsuccessful.empty:
                st.markdown(f"- **Note:** Scope retrieval failed for {len(unsuccessful)} journals. Evaluating on dataset scope descriptions.")

        # ── TABLO GÖRÜNÜMÜ ────────────────────────────────────────────────────
        with tab_table:
            show_cols = [
                "journal_title", "publisher", "subject_area", "sjr_quartile",
                "impact_factor", "sjr_score", "h_index", "issn", "oa_type", "match_pct",
            ]
            # Only show columns that exist
            show_cols = [c for c in show_cols if c in res.columns]
            rename_map = {
                "journal_title":  "Dergi Adı",
                "publisher":      "Yayıncı",
                "subject_area":   "Konu Alanı",
                "sjr_quartile":   "Kuartil",
                "impact_factor":  "Etki Faktörü",
                "sjr_score":      "SJR Skoru",
                "h_index":        "H-indeks",
                "issn":           "ISSN",
                "oa_type":        "OA Türü",
                "cas":            "CAS Eşleşme Skoru",
            }
            display_df = res[show_cols].rename(columns=rename_map)
            st.dataframe(
                display_df,
                use_container_width=True,
                hide_index=True,
            )
            # Download button
            csv_bytes = display_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                "⬇️ CSV Olarak İndir",
                data=csv_bytes,
                file_name="oa_journal_results.csv",
                mime="text/csv",
            )

        # ── ANALİZ ────────────────────────────────────────────────────────────
        with tab_chart:
            import plotly.express as px
            import plotly.graph_objects as go

            c1, c2 = st.columns(2)

            with c1:
                # Publisher distribution
                pub_counts = res["publisher"].value_counts().reset_index()
                pub_counts.columns = ["Yayıncı", "Sayı"]
                fig = px.pie(
                    pub_counts, names="Yayıncı", values="Sayı",
                    title="📊 Yayıncıya Göre Dağılım",
                    color_discrete_sequence=px.colors.qualitative.Set2,
                    hole=0.45,
                )
                fig.update_layout(margin=dict(t=50, b=20, l=10, r=10), height=320)
                st.plotly_chart(fig, use_container_width=True)

            with c2:
                # Subject area bar chart
                sub_counts = res["subject_area"].value_counts().head(8).reset_index()
                sub_counts.columns = ["Konu Alanı", "Sayı"]
                fig2 = px.bar(
                    sub_counts, x="Sayı", y="Konu Alanı",
                    orientation="h",
                    title="🔖 Konu Alanı Dağılımı",
                    color="Sayı",
                    color_continuous_scale="Blues",
                )
                fig2.update_layout(
                    margin=dict(t=50, b=20, l=10, r=10), height=320,
                    coloraxis_showscale=False, yaxis_title=None,
                )
                st.plotly_chart(fig2, use_container_width=True)

            # Match score distribution
            if "cas" in res.columns:
                fig3 = px.histogram(
                    res, x="cas", nbins=20,
                    title="📈 CAS Skoru Dağılımı",
                    labels={"cas": "CAS (%)"},
                    color_discrete_sequence=["#3182ce"],
                )
                fig3.update_layout(margin=dict(t=50, b=30, l=10, r=10), height=260)
                st.plotly_chart(fig3, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# Footer
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("---")
st.markdown(
    "<div style='text-align:center;color:#a0aec0;font-size:.78rem;padding:.5rem 0 1rem'>"
    "🔬 <b>OA Journal Finder</b> — Ege Üniversitesi Kütüphane & Dokümantasyon Daire Başkanlığı &nbsp;|&nbsp; "
    "TÜBİTAK EKUAL Oku &amp; Yayımla Anlaşmaları &nbsp;|&nbsp; "
    "<a href='https://kutuphane.ege.edu.tr' target='_blank' style='color:#3182ce'>kutuphane.ege.edu.tr</a>"
    "</div>",
    unsafe_allow_html=True,
)
