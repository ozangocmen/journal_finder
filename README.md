# 🔬 OpenAccess Journal Finder

**Açık Erişim Dergi Bulucu — Ege Üniversitesi Kütüphane Portalı**

Fonlanan Oku & Yayımla (Read & Publish) anlaşmaları kapsamındaki dergileri yapay zeka ile bulun.

---

## ✨ Özellikler

| Özellik | Açıklama |
|---|---|
| 🏢 Yayıncı Panosu | 10 yayıncıya tıklayarak seçin (SN, Wiley, Elsevier, T&F, CUP, OUP, ACS, RSC, SAGE, IOP) |
| 🤖 AI Eşleştirme | TF-IDF + cosine similarity ile makale–dergi eşleştirme |
| 🏆 Q1 Filtresi | SJR kuartiline göre otomatik filtreleme |
| 🧠 LLM Re-ranking | Claude API ile isteğe bağlı yeniden sıralama |
| 📊 Analitik | Çapraz yayıncı istatistikleri ve görselleştirmeler |
| 📥 Gerçek Veri | Kütüphane sayfasından Excel indirme ve içe aktarma |
| 📤 Dosya Yükleme | Kendi CSV/Excel dosyanızı sisteme dahil edin |

---

## 📁 Klasör Yapısı

```
oa-journal-finder/
│
├── app.py                         # 🏠 Ana Streamlit uygulaması
├── requirements.txt               # Python bağımlılıkları
│
├── .streamlit/
│   └── config.toml                # Streamlit tema & sunucu ayarları
│
├── backend/
│   ├── __init__.py
│   ├── data_loader.py             # CSV/Excel yükleme & normalleştirme
│   ├── matcher.py                 # TF-IDF eşleştirme motoru + LLM re-rank
│   └── scraper.py                 # Kütüphane sayfasından Excel URL bulma
│
├── utils/
│   ├── __init__.py
│   └── enricher.py                # SJR kuartil & IF zenginleştirme
│
├── pages/
│   ├── 1_📚_Publisher_Detail.py   # Yayıncı dergi tarayıcısı
│   ├── 2_📊_Analytics.py          # Çapraz analitik panosu
│   └── 3_🔗_Real_Data_Sync.py     # Gerçek veri indirme & içe aktarma
│
└── data/
    ├── publishers.json            # Yayıncı metadata
    ├── springer_nature.csv        # Springer Nature dergi listesi
    ├── wiley.csv                  # Wiley
    ├── elsevier.csv               # Elsevier
    ├── taylor_francis.csv         # Taylor & Francis
    ├── cambridge.csv              # Cambridge UP
    ├── oxford.csv                 # Oxford UP
    ├── acs.csv                    # ACS
    ├── rsc.csv                    # RSC
    ├── sage.csv                   # SAGE
    └── iop.csv                    # IOP
```

---

## 🚀 Kurulum & Çalıştırma

### 1. Python ortamı oluşturun

```bash
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
```

### 2. Bağımlılıkları yükleyin

```bash
pip install -r requirements.txt
```

### 3. Uygulamayı başlatın

```bash
streamlit run app.py
```

Tarayıcınızda `http://localhost:8501` adresine gidin.

---

## 📊 Gerçek Verilerle Çalışmak

### Seçenek A — Otomatik İndirme (önerilen)
1. Uygulamada **"🔗 Real Data Sync"** sayfasına gidin.
2. İstediğiniz yayıncı satırında **"⬇️ İndir / Güncelle"** butonuna tıklayın.
3. Sistem Ege Üniversitesi Kütüphane sunucusundan Excel'i otomatik indirir ve `data/` klasörüne kaydeder.

### Seçenek B — Manuel Yükleme
1. [kutuphane.ege.edu.tr](https://kutuphane.ege.edu.tr) adresinden Excel dosyasını indirin.
2. "🔗 Real Data Sync" sayfasında **Manuel Dosya Yükleme** bölümüne yükleyin.

### Seçenek C — Doğrudan CSV Yerleştirme
Excel dosyasını şu adımla CSV'ye çevirip `data/` klasörüne koyun:

```python
import pandas as pd
df = pd.read_excel("sn_26_ae_dergi_listesi-v4.xlsx")
df.to_csv("data/springer_nature.csv", index=False)
```

---

## 🤖 AI Eşleştirme Nasıl Çalışır?

```
Kullanıcı Sorgusu (başlık + anahtar kelimeler + özet)
          │
          ▼
    Metin Temizleme (lowercase, özel karakter kaldırma)
          │
          ▼
    TF-IDF Vektörleştirme (bigramlar, sublinear_tf=True)
          │
          ▼
    Cosine Similarity (tüm dergilere karşı)
          │
          ▼
    Q1 Filtresi (SJR Quartile = Q1)
          │
          ▼
    Skor Normalleştirme (0–100%)
          │
          ▼  [isteğe bağlı]
    Claude LLM Re-ranking (Anthropic API)
          │
          ▼
    Sıralı Sonuçlar
```

---

## 🔑 Claude API Re-ranking (İsteğe Bağlı)

TF-IDF sonuçlarını Claude ile gelişmiş AI ile yeniden sıralamak için:

1. [console.anthropic.com](https://console.anthropic.com) adresinden API anahtarı alın.
2. Uygulamanın sol kenar çubuğundaki **"Anthropic API Key"** alanına girin.
3. Arama yapın — Claude top-20 sonucu değerlendirip 0-100 arası puanlar.

---

## ☁️ Dağıtım (Deployment)

### Streamlit Cloud (ücretsiz, önerilen)

```bash
# 1. GitHub'a yükleyin
git init && git add . && git commit -m "initial commit"
git remote add origin https://github.com/kullanici/oa-journal-finder.git
git push -u origin main

# 2. share.streamlit.io adresinde "New app" → repo seçin → app.py
```

### Docker

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8501
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

```bash
docker build -t oa-journal-finder .
docker run -p 8501:8501 oa-journal-finder
```

---

## 🔧 Kendi Verilerinizi Eklemek

### Yeni Yayıncı Eklemek

1. `data/publishers.json` dosyasına yeni giriş ekleyin:

```json
{
  "id": "de_gruyter",
  "name": "De Gruyter",
  "short": "DG",
  "csv_file": "de_gruyter.csv",
  "color": "#6B46C1",
  "bg_color": "#F0EBF8",
  "journal_count": 800,
  "description": "...",
  "agreement_period": "2024–2026",
  "active": true
}
```

2. `data/de_gruyter.csv` dosyasını oluşturun (şu kolonları içermeli):
   `journal_title, issn, subject_area, sjr_quartile, scope`

---

## 📋 CSV Kolon Şeması

| Kolon | Açıklama | Zorunlu |
|---|---|---|
| `journal_title` | Dergi adı | ✅ |
| `issn` | Baskı ISSN | |
| `eissn` | Elektronik ISSN | |
| `subject_area` | Konu alanı | ✅ |
| `subject_category` | Alt konu | |
| `publisher` | Yayıncı adı | ✅ |
| `oa_type` | Hybrid / OA | |
| `sjr_quartile` | Q1/Q2/Q3/Q4 | ✅ |
| `sjr_score` | SJR skoru | |
| `impact_factor` | Etki faktörü | |
| `h_index` | H-indeksi | |
| `scope` | Dergi kapsamı (eşleştirme için kritik) | ✅ |

---

## 🏛️ Desteklenen Yayıncılar

| Yayıncı | Dergi Sayısı | Kaynak |
|---|---|---|
| Springer Nature | ~2,800 | kutuphane.ege.edu.tr |
| Wiley | ~1,700 | kutuphane.ege.edu.tr |
| Elsevier | ~2,900 | kutuphane.ege.edu.tr |
| Taylor & Francis | ~2,700 | kutuphane.ege.edu.tr |
| Cambridge UP | ~420 | kutuphane.ege.edu.tr |
| Oxford UP | ~380 | kutuphane.ege.edu.tr |
| ACS | ~66 | kutuphane.ege.edu.tr |
| RSC | ~44 | kutuphane.ege.edu.tr |
| SAGE | ~1,000 | kutuphane.ege.edu.tr |
| IOP | ~90 | kutuphane.ege.edu.tr |

---

## 📄 Lisans

MIT License — Ege Üniversitesi Kütüphane & Dokümantasyon Daire Başkanlığı kullanımı için serbesttir.
