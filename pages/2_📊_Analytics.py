"""
pages/2_📊_Analytics.py
========================
Analytics dashboard: cross-publisher statistics, subject area maps,
quartile breakdowns, and impact factor distributions.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from backend.data_loader import load_all_publishers, load_publishers

st.set_page_config(
    page_title="Analytics | OA Journal Finder",
    page_icon="📊",
    layout="wide",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
</style>
""", unsafe_allow_html=True)

st.title("📊 Genel Analitik Paneli")
st.caption("Tüm Oku & Yayımla anlaşmaları kapsamındaki fonlanan OA dergilerin istatistiksel görünümü.")

# ── Load all data ──────────────────────────────────────────────────────────────
@st.cache_data(show_spinner="Tüm veriler yükleniyor…")
def _load_all() -> pd.DataFrame:
    return load_all_publishers()

df_all = _load_all()
publishers = load_publishers()
pub_colors = {p["name"]: p["color"] for p in publishers}

if df_all.empty:
    st.error("Veri bulunamadı. Lütfen data/ klasöründe CSV dosyalarının olduğundan emin olun.")
    st.stop()

# ── Summary cards ──────────────────────────────────────────────────────────────
n_total   = len(df_all)
n_q1      = (df_all["sjr_quartile"].str.upper().str.contains("Q1", na=False)).sum()
n_pub     = df_all["publisher"].nunique()
n_subject = df_all["subject_area"].nunique()
pct_q1    = round(n_q1 / n_total * 100, 1) if n_total else 0

cols = st.columns(5)
for col, val, lbl, icon in [
    (cols[0], n_total,    "Toplam Dergi",    "📚"),
    (cols[1], n_q1,       "Q1 Dergi",        "🏆"),
    (cols[2], n_pub,      "Yayıncı",         "🏢"),
    (cols[3], n_subject,  "Konu Alanı",      "🔖"),
    (cols[4], f"{pct_q1}%", "Q1 Oranı",      "📈"),
]:
    col.metric(f"{icon} {lbl}", val)

st.markdown("---")

# ── Row 1: Publisher breakdown + Quartile pie ──────────────────────────────────
r1c1, r1c2 = st.columns(2)

with r1c1:
    pub_q = (
        df_all.groupby("publisher")["sjr_quartile"]
        .apply(lambda s: (s.str.upper().str.contains("Q1", na=False)).sum())
        .reset_index()
    )
    pub_q.columns = ["Yayıncı", "Q1 Dergi Sayısı"]
    pub_total = df_all.groupby("publisher").size().reset_index(name="Toplam")
    pub_merged = pub_q.merge(pub_total, left_on="Yayıncı", right_on="publisher").drop(columns="publisher")

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Q1 Dergi",
        x=pub_merged["Yayıncı"],
        y=pub_merged["Q1 Dergi Sayısı"],
        marker_color="#3182ce",
    ))
    fig.add_trace(go.Bar(
        name="Diğer",
        x=pub_merged["Yayıncı"],
        y=pub_merged["Toplam"] - pub_merged["Q1 Dergi Sayısı"],
        marker_color="#bee3f8",
    ))
    fig.update_layout(
        barmode="stack",
        title="Yayıncıya Göre Q1 / Diğer Dergi Dağılımı",
        xaxis_tickangle=-30,
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        height=380,
        margin=dict(t=60, b=80, l=10, r=10),
    )
    st.plotly_chart(fig, use_container_width=True)

with r1c2:
    q_counts = df_all["sjr_quartile"].value_counts().reset_index()
    q_counts.columns = ["Kuartil", "Sayı"]
    q_counts = q_counts[q_counts["Kuartil"].str.match(r"Q[1-4]", na=False)]

    color_map = {"Q1": "#38a169", "Q2": "#3182ce", "Q3": "#d69e2e", "Q4": "#e53e3e", "Unknown": "#a0aec0"}
    fig2 = px.pie(
        q_counts, names="Kuartil", values="Sayı",
        title="Tüm Dergilerde Kuartil Dağılımı",
        color="Kuartil",
        color_discrete_map=color_map,
        hole=0.45,
    )
    fig2.update_layout(height=380, margin=dict(t=60, b=10, l=10, r=10))
    st.plotly_chart(fig2, use_container_width=True)

# ── Row 2: Top subject areas + IF box plot ─────────────────────────────────────
r2c1, r2c2 = st.columns(2)

with r2c1:
    top_subjects = (
        df_all[df_all["sjr_quartile"].str.upper().str.contains("Q1", na=False)]
        ["subject_area"].value_counts().head(12).reset_index()
    )
    top_subjects.columns = ["Konu Alanı", "Q1 Dergi Sayısı"]

    fig3 = px.bar(
        top_subjects, x="Q1 Dergi Sayısı", y="Konu Alanı",
        orientation="h",
        title="Top 12 Konu Alanı (Q1 Dergi Sayısına Göre)",
        color="Q1 Dergi Sayısı",
        color_continuous_scale="Blues",
    )
    fig3.update_layout(
        height=400, margin=dict(t=60, b=10, l=10, r=10),
        coloraxis_showscale=False, yaxis_title=None,
    )
    st.plotly_chart(fig3, use_container_width=True)

with r2c2:
    # Impact factor distribution per publisher (violin / box)
    if_df = df_all.copy()
    if_df["impact_factor"] = pd.to_numeric(if_df["impact_factor"], errors="coerce")
    if_df = if_df.dropna(subset=["impact_factor"])
    if_df = if_df[if_df["impact_factor"] > 0]

    if not if_df.empty:
        fig4 = px.box(
            if_df, x="publisher", y="impact_factor",
            title="Yayıncıya Göre Etki Faktörü Dağılımı",
            color="publisher",
            color_discrete_sequence=px.colors.qualitative.Set2,
            points="outliers",
        )
        fig4.update_layout(
            height=400, margin=dict(t=60, b=10, l=10, r=10),
            showlegend=False, xaxis_tickangle=-30, xaxis_title=None,
        )
        st.plotly_chart(fig4, use_container_width=True)
    else:
        st.info("Etki faktörü verisi bulunamadı.")

# ── Row 3: OA type breakdown ───────────────────────────────────────────────────
st.markdown("---")
st.subheader("🔓 OA Türü Dağılımı")

if "oa_type" in df_all.columns:
    oa_pub = (
        df_all.groupby(["publisher", "oa_type"]).size().reset_index(name="count")
    )
    fig5 = px.bar(
        oa_pub, x="publisher", y="count", color="oa_type",
        title="Yayıncıya Göre OA Türü (Hybrid / Gold / Full-OA)",
        barmode="group",
        color_discrete_sequence=px.colors.qualitative.Pastel,
    )
    fig5.update_layout(
        height=350, margin=dict(t=60, b=80, l=10, r=10),
        xaxis_tickangle=-30, xaxis_title=None,
        legend_title="OA Türü",
    )
    st.plotly_chart(fig5, use_container_width=True)

# ── Full data table ────────────────────────────────────────────────────────────
st.markdown("---")
with st.expander("🗃️ Tüm Veriyi Göster / İndir"):
    show_cols = [c for c in [
        "journal_title", "publisher", "subject_area", "sjr_quartile",
        "impact_factor", "sjr_score", "oa_type", "issn",
    ] if c in df_all.columns]
    st.dataframe(df_all[show_cols], use_container_width=True, hide_index=True)
    st.download_button(
        "⬇️ Tüm Veriyi CSV Olarak İndir",
        data=df_all[show_cols].to_csv(index=False).encode("utf-8"),
        file_name="all_oa_journals.csv",
        mime="text/csv",
    )
