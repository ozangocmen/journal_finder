"""
pages/3_🔗_Real_Data_Sync.py
==============================
Allows admins to download the REAL journal list Excel files from
Ege University Library pages and save them to the local data/ directory.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import time
import requests
import pandas as pd
import streamlit as st
from backend.data_loader import load_publishers, _normalise_columns, _ensure_required_cols
from backend.scraper import get_download_url, PAGE_URLS

st.set_page_config(
    page_title="Veri Güncelleme | OA Journal Finder",
    page_icon="🔗",
    layout="wide",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
</style>
""", unsafe_allow_html=True)

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

st.title("🔗 Gerçek Veri Senkronizasyonu")
st.caption(
    "Ege Üniversitesi Kütüphanesi Oku & Yayımla anlaşma sayfalarından "
    "gerçek Excel dosyalarını indirip yerel data/ klasörüne kaydedin."
)

publishers = load_publishers()
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; OAJournalFinder/1.0)"}

st.info(
    "⚠️ **Not:** Bu sayfa doğrudan Ege Üniversitesi sunucularına bağlanır. "
    "Sunucu erişilebilir değilse indirme başarısız olabilir. "
    "Yerel CSV dosyaları her zaman yedek olarak kullanılır."
)

st.markdown("---")
st.subheader("📥 Yayıncı Veri Dosyaları")

for pub in publishers:
    col1, col2, col3 = st.columns([3, 2, 2])

    with col1:
        page_url = PAGE_URLS.get(pub["id"], pub.get("oa_url", "#"))
        st.markdown(
            f"**{pub['name']}**  \n"
            f"<small>📄 [Anlaşma Sayfası]({page_url})</small>",
            unsafe_allow_html=True,
        )

    with col2:
        local_path = DATA_DIR / f"{pub['id']}.csv"
        if local_path.exists():
            st.success(f"✅ Yerel CSV mevcut")
        else:
            st.warning("⚠️ Yerel CSV yok")

    with col3:
        if st.button(f"⬇️ İndir / Güncelle", key=f"dl_{pub['id']}"):
            with st.spinner(f"{pub['name']} için veri aranıyor…"):
                url = get_download_url(pub["id"])

            if url:
                st.write(f"🔗 URL bulundu: `{url[:70]}…`")
                try:
                    with st.spinner("İndiriliyor…"):
                        resp = requests.get(url, timeout=30, headers=HEADERS)
                        resp.raise_for_status()

                    from io import BytesIO
                    raw = BytesIO(resp.content)
                    fname = url.lower()
                    if ".xlsx" in fname or ".xls" in fname:
                        df = pd.read_excel(raw, dtype=str)
                    else:
                        df = pd.read_csv(raw, dtype=str)

                    df = _normalise_columns(df)
                    df = _ensure_required_cols(df, pub["name"])
                    df = df.fillna("")

                    # Save as CSV
                    save_path = DATA_DIR / f"{pub['id']}.csv"
                    df.to_csv(save_path, index=False)
                    st.success(f"✅ {len(df)} dergi kaydedildi → `data/{pub['id']}.csv`")
                    st.dataframe(df.head(5), use_container_width=True)

                except Exception as exc:
                    st.error(f"❌ İndirme hatası: {exc}")
            else:
                st.warning(
                    "Bu yayıncı için doğrudan indirme URL'si bulunamadı. "
                    "Anlaşma sayfasını manuel olarak ziyaret edin ve "
                    "Excel dosyasını `data/` klasörüne kaydedin."
                )

    st.markdown("---")

# ── Manual upload section ──────────────────────────────────────────────────────
st.subheader("📤 Manuel Dosya Yükleme")
st.caption(
    "Kütüphane sayfasından indirdiğiniz Excel/CSV dosyasını seçin, "
    "yayıncıyı eşleştirin, ve yerel data/ klasörüne kaydedin."
)

col_a, col_b = st.columns(2)
with col_a:
    manual_pub = st.selectbox(
        "Yayıncı Seçin",
        options=[p["name"] for p in publishers],
        key="manual_pub",
    )
with col_b:
    manual_file = st.file_uploader(
        "Excel veya CSV Dosyası",
        type=["xlsx", "xls", "csv"],
        key="manual_file",
    )

if manual_file and st.button("💾 Kaydet", key="manual_save"):
    pub_id = next(p["id"] for p in publishers if p["name"] == manual_pub)
    from io import BytesIO
    raw = BytesIO(manual_file.read())
    fname = manual_file.name.lower()
    try:
        if fname.endswith(".csv"):
            df = pd.read_csv(raw, dtype=str)
        else:
            df = pd.read_excel(raw, dtype=str)

        df = _normalise_columns(df)
        df = _ensure_required_cols(df, manual_pub)
        df = df.fillna("")

        save_path = DATA_DIR / f"{pub_id}.csv"
        df.to_csv(save_path, index=False)
        st.success(f"✅ {len(df)} dergi kaydedildi → `data/{pub_id}.csv`")
        st.dataframe(df.head(10), use_container_width=True)
    except Exception as exc:
        st.error(f"❌ Dosya işleme hatası: {exc}")
