# Shorts Otomasyonu

Tam otomatik YouTube Shorts uretimi: konu bulur, senaryo yazar, seslendirir, gorselleri toplar,
1080x1920 video kurgular, thumbnail uretir ve YouTube'a yukler.

GitHub Actions uzerinde **her gun otomatik** calisir (`schedule`: 15:17 UTC = 18:17 Turkiye).
Elle ya da cron-job.org ile `workflow_dispatch` tetiklenerek ek video da uretilebilir.

> cron-job.org da hala tetikliyorsa gunde birden fazla video cikar. Gunde sadece 1 video
> istiyorsan cron-job.org'daki isi kapat.

---

## Render motoru: motion-engine (varsayilan)

Videolar [motion-engine](https://github.com/oguzhankayan/motion-engine) ile uretilir: Gemini'nin yazdigi ayni
storyboard (`scenes`: arka plan, obje, karakter, ifade, etiket) **sinematik, kodla cizilen sahnelere** donusur.
AI gorseli veya ucretli servis gerekmez; her video ayni gorsel dili korur.

- **12 ortam:** sisli cam ormani, gece, deniz (dalga + ay yansimasi), gokyuzu (bulut katmanlari), kar, col,
  magara, yagmurlu sokak, oda, ofis, laboratuvar, soyut karanlik.
- **Objeler:** deniz feneri (donen isik), gemi, ucak (yanip sonen isiklar), ev, araba (farlar), kapi, pencere,
  telefon, telsiz, kamera, mezar, agac...
- **Yakin planlar:** `clock` dijital saat (etiketteki saat, or. `08:45`), `footprints` camurda ayak izleri,
  `letter`/`map` masada belge ya da harita.
- Konu kisisi kadrodaki renklerle (`cast.subject`) arkadan cizilir; korkunca titrer, `walk` pozunda yurur.
- Kanal kimligi korunur: Anton fontlu sari **karaoke altyazi**, ustte manset, daktilolu **CASE FILE** karti,
  SUBSCRIBE / WATCH NEXT, kose logosu; sahne kesmelerinde whoosh, acilista boom.
- Ses: edge-tts anlatimi + sentezlenen orman/ugultu yatagi; anlatim konusurken yatak otomatik geri cekilir.

Dosyalar: `motion/scene.js` (sahne motoru), `motion/render.mjs` (paralel kare render + ses karisimi + MP4),
`motion/sfx.mjs` (ozgun ses efektleri). Actions, motion-engine'i sabit bir commit'ten `motion-engine/` klasorune indirir.

**Yedekler:** motion-engine kurulamaz ya da hata verirse video otomatik olarak asagidaki Remotion stickman
motoruyla, o da olmazsa MoviePy ile uretilir. Hat asla kirilmaz. Eski motoru secmek icin `RENDER_MOTORU=remotion`.

Yerelde:

```bash
git clone https://github.com/oguzhankayan/motion-engine.git
cd motion-engine && git checkout 1926c1126ced9afe1419946f2513c4b6c222b3d1 && npm ci && npx playwright-core install chromium && cd ..
set UPLOAD_TO_YOUTUBE=0
python shorts_otomasyon.py      # RENDER_MOTORU varsayilan olarak motion-engine
```

---

## Yedek animasyon motoru (Remotion): konusan cop adam (stickman)

Videolar **kalin siyah konturlu, buyuk yuvarlak kafali, duz renkli 2D cop adam** tarzindadir
(`remotion/src/stickman/`). Karakterler ve dekor **kodla (SVG) cizilir**, AI gorseli kullanilmaz:
her videoda birebir ayni cizim dili, hizli ve dis servise bagimsiz render (~2 dk).

1. Gemini senaryoyla birlikte bir **kadro** (`cast`: konu kisisinin sac, renk, gozluk, biyik...) ve
   7-10 sahnelik **storyboard** (`scenes`: arka plan, obje, kim var, yuz ifadesi, poz, tabela) yazar.
2. Remotion bu plani canlandirir:
   - sabit **anlatici** karakter (kel, yuvarlak kafa, beyaz tisort) + hikayenin kisileri
   - **agiz anlatimla senkron konusur**, gozler kirpar, nefes alir; sok olunca ziplar, korkunca titrer
   - pozlar: isaret etme, eller havada, eller basta, omuz silkme, yurume
   - 12 arka plan (gece, deniz, oda, orman, ofis, lab, kar...) ve 22 obje (fener, saat, kapi,
     telefon, ucak, gemi, mektup, kafatasi...)
   - karaoke altyazi, ustte manset, daktilolu **CASE FILE** karti, SUBSCRIBE / WATCH NEXT,
     sahne gecislerinde "whoosh" + "pop" sesi
3. Thumbnail, en carpici sahnenin (sok/korku) yazisiz karesinden uretilir.

Eski stile donmek icin: `RENDER_STIL=illustrasyon` (AI ile cizilen karanlik illustrasyon) ya da
`RENDER_MOTORU=moviepy` (stok klip montaji).

Yedekler: AI gorseli yeterince cikmazsa stok klip/fotolara gecilir; Remotion herhangi bir sebeple
hata verirse video eski MoviePy motoruyla uretilir. Yani hat asla kirilmaz.

Eski motora donmek icin: `RENDER_MOTORU=moviepy` (Actions'ta elle tetiklerken `motor` secimi).

Onizleme (yerelde): `cd remotion && npm install && npm run studio`

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
3. **Kod tarafinda dogrulama** - Gemini'nin onerdigi fikir su dordunden herhangi biriyle
   cakisirsa reddedilir ve yeniden uretim istenir (8 denemeye kadar):
   - **Konu / vaka adi**: gecmistekilerle ayni **vaka adini** (`dyatlov`, `roanoke`, `celeste`
     gibi ayirt edici kelimeler) tasiyorsa -> ayni hikaye.
   - **Baslik**: gecmisteki bir baslikla birebir (normalize edilmis) ayni ya da cok benzer olamaz.
     Ayni baslik ASLA iki kez cikmaz - hem ilk (siki) hem son (gevsek) denemelerde uygulanir.
   - **Aciklama**: gecmisteki bir aciklamayla birebir ayni ya da cok benzer olamaz. Bu yuzden
     aciklama metni de `gecmis.json`'a (SEO'suz ham hali) yazilir ve karsilastirilir.
   - **Hook**: acilis cumlesi gecmistekiyle cok benzerse reddedilir.

   Hicbir benzersiz fikir cikmazsa kosu **bilerek iptal edilir** - tekrar video yayinlamaktansa
   o kosuyu atlamak tercih edilir.

4. **Gorseller asla tekrar etmez** - her kullanilan klip/foto URL'si `kullanilan_gorseller.txt`'e
   yazilir ve **tum gecmis kalici olarak yasaklidir** (eski surumdeki 60'lik kayan pencere
   kaldirildi). Ayni stok klip/foto iki farkli videoda bir daha gorunmez; kaynak havuzu
   tukendiginde sistem, her sahnede rastgele seed ile **benzersiz** AI gorseli uretmeye duser.

`expedition`, `shipwreck` gibi yaygin kelimelerin ortak olmasi tek basina red sebebi degildir;
sadece ayirt edici ozel isimler tekrari tetikler. Not: sistem bilerek **siki** taraftadir -
ara sira gercekten ozgun bir konuyu da reddedebilir; bunun bedeli tek bir yeniden-uretim
denemesidir, buna karsilik hicbir konu/baslik/aciklama/gorsel iki kez yayina cikmaz.

---

## Yaratici yon: videolar birbirine benzemesin (Faz 1)

Amac, siradan AI Shorts'undan cikip belgesel tonuna gecmek. Senaryo asamasinda su kurallar
hem Gemini prompt'una yazili hem de **kod tarafinda zorunlu** (ihlal edilirse fikir reddedilip
yeniden uretilir):

1. **Klise kelime yasagi** - `vanished, disappeared, missing, unsolved, lost forever,
   gone without a trace, nobody knows, to this day, never found, never seen again...` script ve
   baslikta YASAK. Bunun yerine olayi ETIKETLEME, olayin somut fiziksel gercegini anlat:
   "The man vanished" degil -> "The elevator reached the top floor empty."
2. **Celiski ile acilis** - ilk cumle isimle, tarihle, sehir adiyla, soruyla ya da "Did you know"
   ile baslayamaz. Dogrudan, izleyicinin beynini durduran bir CELISKI olmali. (Kod; yil/ay ile
   baslamayi, soru ile baslamayi ve klise kaliplari reddeder.)
3. **Konu turu rotasyonu** - her video 16 turden birini secer (`true crime, maritime, aviation,
   old documents, strange object, radio signal, cctv footage, lab finding, cold war file...`) ve
   turu son videolarinkiyle ayni olamaz. Boylece art arda "kaybolan insan" videolari uretilmez.
   Secilen tur `gecmis.json`'a yazilip rotasyon takip edilir.
4. **Profesyonel gorsel sorgular** - tek kelime yasak. Her sahne icin `SUBJECT + SETTING +
   LIGHT/WEATHER` kalibinda, gerektiginde `aerial/close-up/macro/drone shot` gibi cekim kelimeleriyle,
   anlatim sirasina dizili, o an konusulan tek onemli detaya odaklanan aramalar.
5. **Gercek, isimli, tarihli vaka zorunlulugu** - her hikaye YASANMIS, belgelenmis bir olay olmali:
   gercek kisi/gemi/ucak/yer ADI ve gercek YIL gecmeli. "Bir adam / bir kadin / yillar once" gibi
   jenerik-uydurma cerceveleme yasak; ilk ~8 saniyede gercek isim + yil + yer verilir (kanca yine
   celiskiyle acilir, isim kancada olabilir ama duz tarihle acilis yasak). Kod tarafinda: script bir
   yil/tarih (4 haneli yil ya da AD/BC/century) icermiyorsa fikir reddedilip yeniden uretilir.

### Faz 2: sinematik render katmani (aktif)

Video kurulduktan sonra ham dosyaya **tek bir FFmpeg son-islem pasi** uygulanir (`_sinematik_pas`):

- **Soguk belgesel gradesi** - `eq` + `colorbalance` ile hafif kontrast, dusuk doygunluk, soguk ton.
- **Film grain** - `noise` (temporal); dogal bir titreme/arsiv dokusu verir, "AI slop" hissini kirar.
- **Vignette** - kenar karartma, dikkat merkeze toplanir.
- **Ambient ugultu** - anlatimin cok altinda, FFmpeg `anoisesrc` (brown noise) ile **sentezlenen**
  derin bir ses yatagi. Harici ses asseti gerektirmez.

Pas, en zengin zincirden en sadeye dogru geriler; hicbir varyant calismazsa ham video oldugu gibi
kullanilir, yani render hatti asla kirilmaz. `imageio-ffmpeg`'in getirdigi ffmpeg binary'si kullanilir.

Ortam degiskenleriyle ayarlanir:

| Degisken | Varsayilan | Ne yapar |
|---|---|---|
| `SINEMATIK` | `1` | Sinematik pasi ac/kapat (`0` = ham video) |
| `SINEMATIK_GRAIN` | `7` | Film grain siddeti (0-20) |
| `AMBIENT_SES` | `1` | Ambient ugultu ses yatagi |
| `AMBIENT_VOL` | `0.16` | Ambient sesin seviyesi (anlatimin altinda kalmali) |
| `VHS` | `0` | Opsiyonel analog doku (renk kaymasi + dusuk doygunluk); arsiv/CCTV hissi |

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
`X264_PRESET`, `UPLOAD_TO_YOUTUBE`, `MANUAL_MODE`, `RENDER_MOTORU` (`remotion` / `moviepy`).

Remotion motoru icin Node.js 18+ gerekir: `cd remotion && npm install` (ilk calistirmada headless
Chrome otomatik indirilir).

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
