# 🎯 Lead Finder

Web tasarım işi için **potansiyel müşteri (lead) bulma** sistemi.

Şehir + ilçe + sektör girersiniz; sistem **OpenStreetMap** (ücretsiz, açık kaynak)
üzerinden işletmeleri bulur, web sitelerini teknik olarak analiz eder, her işletmeye
**0-100 arası bir Lead Skoru** verir ve en iyi potansiyel müşterileri size panelde sıralar.

> **Tamamen ücretsiz çalışır.** Hiçbir ücretli API zorunlu değildir. Yapay zeka
> tamamen opsiyoneldir (varsayılan olarak **kapalıdır**).

---

## ⚡ 5 Dakikada Kurulum (Adım Adım)

Bilgisayarınızda sadece **Python 3.10 veya üstü** olması yeterlidir.
(Kontrol: terminale `python3 --version` yazın.)

### 1) Bu klasöre girin

```bash
cd lead-finder
```

### 2) Sanal ortam oluşturun (önerilir)

**Mac / Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

**Windows (PowerShell):**
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 3) Gerekli paketleri kurun

```bash
pip install -r requirements.txt
```

### 4) (Opsiyonel) Ayar dosyasını oluşturun

`.env` dosyası oluşturmadan da sistem çalışır. İsterseniz varsayılanları
değiştirmek için örnek dosyayı kopyalayın:

```bash
cp .env.example .env
```

### 5) Başlatın

```bash
python run.py
```

Tarayıcınızdan şu adresi açın: **http://127.0.0.1:8000**

Bitti! 🎉

---

## 🖱️ Nasıl Kullanılır?

1. Üstteki menüden **"İşletme Ara"** sayfasına gidin.
2. **Şehir**, **İlçe**, **Sektör** ve **maksimum işletme sayısı** girin.
   - Örnek: `İstanbul` / `Avcılar` / `Diş Kliniği` / `100`
3. **"Ara ve Analiz Et"** butonuna basın. Sistem:
   - İşletmeleri bulur ve veritabanına kaydeder (aynı işletmeyi tekrar eklemez),
   - Web sitesi olup olmadığını kontrol eder,
   - Web sitesi varsa teknik analiz yapar,
   - Lead skoru hesaplar.
4. **"Lead Listesi"** sayfasından sonuçları filtreleyin/sıralayın.
5. Bir işletmeye tıklayıp **detay sayfasında** şunları yapın:
   - Lead skorunu ve nedenlerini görün,
   - Hazır **WhatsApp / e-posta satış mesajı taslaklarını** kopyalayın,
   - **CRM durumu**, **not** ve **takip tarihi** ekleyin,
   - İşletmeye özel **demo site** oluşturun.

> ℹ️ **Arama biraz sürebilir.** Her işletmenin web sitesi tek tek ziyaret edilip
> analiz edildiği ve kaynaklara nazik davranmak için istekler arasında bekleme
> uygulandığı için, 100 işletmelik bir arama birkaç dakika alabilir.

---

## 🧠 Lead Skoru Nasıl Hesaplanır?

Her işletmeye **0-100** arası bir puan verilir. Puan yükseldikçe potansiyel artar:

| Puan | Seviye |
|------|--------|
| 80-100 | 🔥 **HOT** (en sıcak) |
| 60-79 | 🌡️ **WARM** |
| 40-59 | **POSSIBLE** |
| 0-39 | **LOW** |

Puanı belirleyen etkenler (ağırlıklar `app/config.py` içinde değiştirilebilir):

- **Web sitesi yok** → en güçlü sinyal (+40 ve online varlık tamamen eksik sayılır)
- HTTPS / SSL problemi
- Mobil uyumluluk zayıf
- Site çok yavaş
- Modası geçmiş / eski tasarım
- Meta etiketleri (title / description) eksik
- İletişim bilgileri yetersiz
- Online randevu / rezervasyon yok

**Puanlamayı değiştirmek** için `app/config.py` içindeki `SCORING_WEIGHTS`
sözlüğünü düzenlemeniz yeterlidir.

---

## 🤖 Yapay Zeka (Opsiyonel)

Sistem AI olmadan **tam olarak çalışır**. Ekstra yorum istiyorsanız `.env` içinde
`AI_MODE` değerini değiştirin:

| Değer | Anlamı |
|-------|--------|
| `none` | **Varsayılan.** AI kapalı, tamamen ücretsiz. |
| `ollama` | Yerel Ollama modeli (ücretsiz). Önce [ollama.com](https://ollama.com) kurulmalı. |
| `claude` | Anthropic Claude API (**ücretli**, API anahtarı gerekir). |

**Ollama ile ücretsiz kullanım:**
```bash
# Ollama'yı kurun (ollama.com), sonra bir model indirin:
ollama pull llama3.1
# .env içinde:  AI_MODE=ollama
```

AI açıkken işletme detay sayfasında **"AI ile Değerlendir"** butonu çıkar. AI;
web sitesi kalitesini yorumlar, lead değerlendirmesi yapar ve satış fırsatı önerir.

---

## 🌐 Demo Site Sistemi

Her işletme için sektöre uygun, **hazır şablona** dayalı modern bir demo sayfası
oluşturabilirsiniz. Şablonlar responsive, mobil uyumlu ve Türkçedir.

Desteklenen şablonlar: **Diş kliniği, Güzellik merkezi, Restoran, Kuaför, Emlak, Oto servis.**

- İşletme bilgileri (ad, telefon, adres…) otomatik yerleştirilir.
- **Uydurma yorum / sahte fiyat / sahte çalışan üretilmez.** Eksik bilgi için
  "Bilgi eklenebilir" yazar.
- Her demo sayfasında görünür şekilde *"Bu sayfa örnek/demo tasarım olarak
  hazırlanmıştır."* ibaresi bulunur.
- Demo adresi: `http://127.0.0.1:8000/demo/isletme-adi`

---

## 📁 Proje Yapısı

```
lead-finder/
├── run.py                     # Başlatma betiği
├── requirements.txt           # Python bağımlılıkları
├── .env.example               # Örnek ayarlar
└── app/
    ├── main.py                # FastAPI uygulaması
    ├── config.py              # Ayarlar + LEAD PUANLAMA ağırlıkları
    ├── database.py            # SQLite bağlantısı
    ├── models.py              # Veritabanı tabloları
    ├── scoring.py             # Lead skorlama motoru
    ├── phone.py               # Telefon normalizasyonu (+90...)
    ├── http_client.py         # Rate-limit + User-Agent
    ├── providers/             # 🔌 VERİ KAYNAKLARI (modüler)
    │   ├── base.py            #    Ortak yapı + sektör→OSM eşlemesi
    │   ├── overpass.py        #    OpenStreetMap / Overpass API
    │   ├── openstreetmap.py   #    Nominatim (adres→koordinat)
    │   ├── future_provider.py #    Yeni kaynak eklemek için şablon
    │   └── registry.py        #    Aktif kaynak listesi
    ├── services/
    │   ├── collector.py       # Arama→kaydet→analiz→skor orkestrasyonu
    │   ├── website_analyzer.py# Web sitesi teknik analizi
    │   ├── ai.py              # Opsiyonel AI (none/ollama/claude)
    │   ├── messages.py        # Satış mesajı taslakları
    │   └── demo.py            # Demo site üretimi
    ├── routers/               # Sayfa ve API rotaları
    └── templates/             # Panel + demo şablonları (HTML)
```

---

## 🗄️ Veritabanı

Varsayılan olarak **SQLite** kullanılır — kurulum gerektirmez, veriler
`lead_finder.db` dosyasında saklanır. Dört tablo vardır:
`businesses`, `website_analysis`, `leads`, `demo_sites`.

İleride **Supabase / PostgreSQL**'e geçmek isterseniz sadece `.env` içindeki
`DATABASE_URL` değerini değiştirmeniz yeterlidir (kod değişikliği gerekmez).

---

## ➕ Yeni Veri Kaynağı Ekleme (Geliştiriciler İçin)

1. `app/providers/future_provider.py` dosyasını örnek alarak yeni bir provider yazın.
2. `search()` metodunu doldurup `RawBusiness` listesi döndürün.
3. `app/providers/registry.py` içindeki `ACTIVE_PROVIDERS` listesine ekleyin.

Sistemin geri kalanı (kaydetme, tekilleştirme, analiz, skorlama) otomatik çalışır.

---

## 🔒 Veri Güvenliği ve Etik Kurallar

Bu sistem bilinçli olarak:

- ❌ Google Maps'i agresif scrape **etmez**, CAPTCHA / erişim engeli **aşmaz**.
- ❌ Giriş gerektiren sistemlere izinsiz **erişmez**.
- ❌ **Otomatik WhatsApp / e-posta mesajı göndermez** (yalnızca taslak hazırlar; gönderimi siz elle yaparsınız).
- ❌ Toplu spam **göndermez**.
- ✅ Sadece **herkese açık** işletme bilgilerini işler.
- ✅ Kaynaklara **rate limit** uygular ve `User-Agent` gönderir.
- ✅ Her kaydın **kaynağını** saklar.
- ✅ **Silme** özelliği sunar.

Veriler [OpenStreetMap](https://www.openstreetmap.org/copyright) kaynaklıdır ve
ODbL lisansına tabidir.

---

## ❓ Sık Karşılaşılan Sorunlar

- **"Arama sonuç döndürmedi."** İnternet bağlantınızı kontrol edin. Sektör adının
  desteklenenlerden biri olduğundan emin olun (panelde öneri listesi çıkar). Bazı
  küçük ilçelerde OpenStreetMap verisi az olabilir; daha büyük bir ilçe deneyin.
- **"Sektör tanınmıyor" hatası.** Desteklenen sektörler: diş kliniği, güzellik
  merkezi, restoran, kuaför, emlak, oto servis, cafe, otel, eczane, veteriner,
  spor salonu. Yeni sektör eklemek için `app/providers/base.py` içindeki
  `SECTOR_OSM_TAGS` sözlüğüne bir satır ekleyin.
- **Site analizleri yavaş.** Normaldir; her site tek tek ziyaret edilir ve
  kaynaklara nazik davranmak için bekleme uygulanır. `.env` içindeki
  `REQUEST_DELAY_SECONDS` değerini düşürebilirsiniz (dikkatli olun).

---

## 🚀 Yayına Alma (İleri Seviye — Opsiyonel)

MVP tamamen yereldir. İnternete açmak isterseniz:

- **Veritabanı:** `DATABASE_URL`'i Supabase/PostgreSQL'e çevirin.
- **Sunucu:** `uvicorn app.main:app --host 0.0.0.0 --port 8000` ile herhangi bir
  Python hosting'de (Railway, Render, Fly.io ücretsiz katmanları) çalışır.
- Panel şu an kimlik doğrulaması içermez; herkese açık bir sunucuya koyacaksanız
  önüne bir giriş katmanı (ör. reverse proxy basic-auth) eklemeniz önerilir.
```

## Geliştirme Aşamaları (yol haritası)

Sistem aşağıdaki sırayla, her aşaması çalışır durumda geliştirilmiştir:

- ✅ **Phase 1** — Kurulum, veritabanı, dashboard
- ✅ **Phase 2** — OpenStreetMap / Overpass ile işletme bulma
- ✅ **Phase 3** — Kaydetme + duplicate detection
- ✅ **Phase 4** — Web sitesi analiz sistemi
- ✅ **Phase 5** — Lead scoring
- ✅ **Phase 6** — CRM (durum, not, takip)
- ✅ **Phase 7** — Demo template sistemi
- ✅ **Phase 8** — Ollama / Claude AI entegrasyonu (opsiyonel)
- ⬜ **Phase 9** — Deployment (yol haritası yukarıda)
