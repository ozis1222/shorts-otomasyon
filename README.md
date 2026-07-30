# Shorts Otomasyonu

Tam otomatik YouTube Shorts uretimi: konu bulur, senaryo yazar, seslendirir, gorselleri toplar,
1080x1920 video kurgular, thumbnail uretir ve YouTube'a yukler.

GitHub Actions uzerinde `workflow_dispatch` ile calisir (cron-job.org tetikler).

---

## Kurulum: gerekli GitHub Secret'lari

`Settings > Secrets and variables > Actions > New repository secret`

| Secret | Zorunlu | Nereden alinir |
|---|---|---|
| `GEMINI_API_KEY` | **Evet** | https://aistudio.google.com/apikey (ucretsiz) |
| `CLIENT_SECRET_JSON` | **Evet** | Google Cloud Console > Credentials > OAuth Desktop app JSON'unun tam icerigi |
| `TOKEN_JSON` | **Evet** | `python yenile_token.py` ile uretilen `token.json` dosyasinin tam icerigi |
| `PIXABAY_API_KEY` | Hayir | https://pixabay.com/api/docs/ (ucretsiz) |
| `PEXELS_API_KEY` | **Onerilir** | https://www.pexels.com/api/ (ucretsiz) |

### `PEXELS_API_KEY` neden onemli?

Gorsel kalitesinin en buyuk kaynagi. Pexels `orientation=portrait` destekler, yani **dikey 4K klip**
verir. Pixabay'de klipler cogunlukla yatay 1920x1080'dir; bunu 1080x1920 dikey cerceveye sigdirmak
icin %78 buyutmek gerekir ve goruntu bulaniklasir. Kod bu tur kaynaklari artik **reddediyor**, bu
yuzden Pexels anahtari yoksa gercek klip yerine cogunlukla AI gorseli kullanilir.

Anahtari ekledigin anda videolarda gercek hareketli, kristal net klip orani ciddi sekilde artar.

---

## Kalite nasil garanti ediliyor?

Kod, her kaynak icin **buyutme orani** hesaplar: kaynagi 1080x1920 cerceveye tam oturtmak icin
gereken olcek. `1.0` = hic buyutme yok.

| Kaynak | Buyutme | Sonuc |
|---|---|---|
| 1080x1920 dikey | x1.00 | kabul |
| 2160x3840 dikey 4K | x0.56 | kabul (kucultuluyor, en net) |
| 1920x1080 yatay HD | x1.78 | **reddedilir** |
| 1280x720 | x2.67 | **reddedilir** |

Sahne basina oncelik sirasi:

1. **Kristal net gercek klip** (buyutme <= 1.25) - hem hareket hem kalite
2. **AI gorseli** (Pollinations, 1440x2560 istenir) - konuya %100 ozel, sinematik zoom+kaydirma
3. **Gevsek esikli klip** (buyutme <= 1.90) - hareket kaybolmasin diye
4. **Stok foto** - son care, LANCZOS buyutme + unsharp mask ile netlestirilir

Cikti kodlamasi: `libx264 preset=medium`, `16 Mbps`, `yuv420p`, `+faststart`.

Sahne gecisleri **sert kesme** ile yapilir: hem Shorts'ta daha vurucu, hem de crossfade'e
gore render suresini 4 kat dusuruyor (olculdu: 200 ms/kare -> 52 ms/kare).

---

## "Ayni hikaye asla tekrar etmesin" nasil calisiyor?

Uc katman:

1. **Kalici hafiza** - `gecmis.json` her uretilen konuyu, basligi ve hook'u saklar. GitHub Actions
   bu dosyayi her kosudan sonra repoya geri commit eder, yani hafiza asla kaybolmaz.
   (Eski surumde `kullanilan_konular.txt` commit edilmiyordu; bu yuzden model her seferinde
   sifirdan basliyor ve ayni vakalari tekrar anlatiyordu. Asil tekrar sebebi buydu.)
2. **Kanaldan tohumlama** - ilk kosuda YouTube'daki **zaten yayinlanmis** video basliklarini da
   hafizaya ekler. Yani `gecmis.json` olusmadan once yuklenmis hikayeler de tekrar edilmez.
3. **Kod tarafinda dogrulama** - Gemini'nin onerdigi konu, gecmistekilerle ayni **vaka adini**
   (`dyatlov`, `roanoke`, `celeste` gibi ayirt edici kelimeler) tasiyorsa reddedilir ve yeniden
   uretim istenir. 8 denemeye kadar surer. Hicbir benzersiz fikir cikmazsa kosu **bilerek iptal
   edilir** - tekrar video yayinlamaktansa o kosuyu atlamak tercih edilir.

`expedition`, `shipwreck` gibi yaygin kelimelerin ortak olmasi tek basina red sebebi degildir;
sadece ayirt edici ozel isimler tekrari tetikler.

---

## Kendini gelistirme

Her kosuda, senaryo yazilmadan once:

- **Kendi kanalinin** en cok ve en az izlenen videolari cekilir (`performans.json`)
- **Nisteki viral Shorts** basliklari toplanir (`viral_ornekler.json`, 20 saat onbellek)

Bu veriler Gemini'ye **sadece veri olarak** verilir: "bunlarin neden tuttugunu incele, ayni
duygusal tetigi kullan, ama tamamen farkli bir hikaye anlat, hicbirini kopyalama."

> Bu ozellik `token.json`'da `youtube.readonly` yetkisi ister. Eski token'inda bu yetki yok.
> `python yenile_token.py` calistirip `TOKEN_JSON` secret'ini guncelle. Guncellemezsen otomasyon
> calismaya devam eder, sadece ogrenme katmani atlanir.

---

## Thumbnail

Videonun en carpici karesi otomatik secilir (detay + parlaklik puanlamasi), kontrast/doygunluk
artirilir, vinyet ve alt karartma eklenir, uzerine Gemini'nin urettigi 2-4 kelimelik vurucu yazi
kalin sari + siyah kenarlikla basilir.

> Ozel thumbnail yuklemek icin YouTube kanalinin **dogrulanmis** olmasi gerekir.
> https://youtube.com/verify adresinden telefonla dogrula. Dogrulanmamissa video yine yuklenir,
> sadece thumbnail atlanir.

---

## Yerelde calistirma

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

set GEMINI_API_KEY=...
set PEXELS_API_KEY=...
set UPLOAD_TO_YOUTUBE=0      # sadece video uret, yukleme yapma
python shorts_otomasyon.py
```

Ayarlanabilir ortam degiskenleri: `GEMINI_MODEL`, `VOICE`, `PRIVACY`, `VIDEO_BITRATE`,
`X264_PRESET`, `UPLOAD_TO_YOUTUBE`, `MANUAL_MODE`.

---

## Guvenlik

API anahtarlari **koda yazilmaz**, yalnizca ortam degiskeninden okunur. Repo public oldugu icin
koda yazilan her anahtar internette yayinlanmis sayilir.

`client_secret.json` ve `token.json` `.gitignore`'dadir; repoya asla commit etme.

---

## Para kazanma (YPP) notlari

Sart: 1.000 abone + son 90 gunde 10 milyon gecerli Shorts izlenmesi.

Otomasyonun bunu destekleyen tarafi:
- Her video **ozgun** anlatim ve ozgun kurgu icerir, tekrar iceriği uretmez (yeniden kullanilmis
  icerik YPP'de en sik red sebebidir).
- Sabit kanal kimligi: kose logosu, ayni altyazi stili, ayni ses.
- Ortada `SUBSCRIBE`, sonda `WATCH NEXT` cagrisi -> abone ve oturum suresi.
- Aciklamada diger videolara yonlendiren sabit satir.

Senin yapman gerekenler: kanal dogrulama, duzenli yayin tempo, ve `PEXELS_API_KEY` eklemek.
