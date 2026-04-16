#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# run.sh  —  OA Journal Finder: setup & launch
# Usage:  bash run.sh
# ─────────────────────────────────────────────────────────────────────────────

set -e

echo ""
echo "🔬 OA Journal Finder — Kurulum & Başlatma"
echo "══════════════════════════════════════════"

# 1. Python check
if ! command -v python3 &>/dev/null; then
  echo "❌ Python 3 bulunamadı. Lütfen Python 3.9+ kurun."
  exit 1
fi
PYTHON=$(command -v python3)
echo "✅ Python: $($PYTHON --version)"

# 2. Virtual environment
if [ ! -d "venv" ]; then
  echo "📦 Sanal ortam oluşturuluyor…"
  $PYTHON -m venv venv
fi

# 3. Activate
source venv/bin/activate 2>/dev/null || source venv/Scripts/activate 2>/dev/null

# 4. Install deps
echo "📥 Bağımlılıklar yükleniyor…"
pip install -q --upgrade pip
pip install -q -r requirements.txt

# 5. Launch
echo ""
echo "🚀 Uygulama başlatılıyor → http://localhost:8501"
echo ""
streamlit run app.py \
  --server.port 8501 \
  --server.address localhost \
  --browser.gatherUsageStats false
