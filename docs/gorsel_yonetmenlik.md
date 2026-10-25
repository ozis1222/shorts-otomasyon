# Görsel yönetmenlik — Unsadark Shorts

## 1. Mevcut sistem (inceleme, 25.10.2026)

| Aşama | Nerede | Önceki durum |
|---|---|---|
| Hikâye + storyboard | `shorts_otomasyon.py` → `_prompt_kur`, `gemini_uret` | Gemini her sahne için `image_prompt` yazıyordu; kamera, ışık ve metin planı yoktu |
| Görsel üretimi | `flux_sahneleri` → `cf_gorsel` (Cloudflare Workers AI, `flux-2-klein-4b`, 864x1536 → 1080x1920) | Tek stil (`_CF_STIL`): düz renkli webcomic; ışık ve plan ölçeği tarif edilmiyordu |
| Kurgu | `remotion_olustur` → `remotion/src/MysteryShort.tsx` | 8 görsel, 3,6 sn'lik sabit kesimlerle 14 sahneye **döngüyle** yayılıyordu: görsel 0, hikâyenin ortasında yeniden çıkıyor, anlatımla bağı kopuyordu |
| Kamera / geçiş | `_KAMERALAR`, `_GECISLER` sabit listeleri | Sahne içeriğinden bağımsız sırayla dönüyordu (pushIn, panLeft, …; zoom, glitch, flash, iris) |
| Üst kırmızı bant | `components/Marka.tsx` → `Manset` | Thumbnail yazısı tüm video boyunca üstte kırmızı bantta duruyordu |
| Altyazı | `components/Altyazi.tsx` | 118 px, ekranın %60'ında; anahtar kelimeler kırmızı kutuda |
| CTA | `Cta` (SUBSCRIBE / WATCH NEXT) | Ekranın ortasında, ana nesnenin üstünde |
| Logo | `Logo` | Sağ alt köşede, YouTube düğmelerinin arkasında |
| Ses efekti | `_ses_efektleri_uret` (FFmpeg sentezi) | Her kesimde whoosh, sahneye özel efekt yoktu |
| Kalite kontrolü | `kalite_kontrol.py` | Yalnızca teknik ve metadata kontrolleri; görsel kontrol yoktu |

## 2. Yeni yaklaşım

**Stil.** Mevcut çizgi dili korunuyor (anime değil). İki varyant var:

- **A:** cilalı 2D çizim; temiz kalın kontur, yumuşak gölgeleme, net yüz ifadesi ve beden dili.
- **B (varsayılan, 25.10.2026 seçimi):** sinematik çizim karesi; düşük anahtar ışık, hafif pus, ana nesne çok yakın, daha az yazı.

İkisinde de ortak olanlar: tek net odak, ön/orta/arka plan derinliği, koyu lacivert ve siyah gölge, tek kontrollü sıcak sarı ışık kaynağı. Prompt'a ayrıca "görselde yazı yok" ve "doğal eller" kuralları ekli.

**Yönetmen planı.** Gemini artık her sahne için şunları da üretiyor: `narration` (sahnenin kapsadığı anlatım cümleleri), `purpose`, `focus`, `emotion`, `shot`, `move`, `light`, `on_screen_text`, `continuity` ve `sfx`. Bunlara ek olarak video başına bir `hook_text` ve bir `look_bible` var:

- `look_bible`: karakterlerin yaş, yüz, saç ve kıyafetini sabitleyen cümle. Her görsel prompt'una eklenir.
- `hook_text`: ilk karedeki tek kanca. Başlıktan, thumbnail yazısından ve ilk anlatım cümlesinden farklı olmak zorunda; önceki videoların kancaları prompt'a verilir, tekrar edilmez.

**Kurgu.**
- Her görsel **bir kez** kullanılıyor ve kendi anlatım parçasının başladığı kelimede açılıyor (`anlatim_baslangiclari`).
- 1,4 sn'den kısa kalacak sahne bir öncekiyle birleştiriliyor.
- Kamera hareketi plandan geliyor ve ölçülü:
  - `push_in`: 1,04 → 1,16 (gerilim, ortaya çıkış)
  - `pull_out`: yalnızlık, sonrası
  - `pan`: arama, bakışı takip
  - `static`: şok anı
  - Aynı hareket üst üste üç kez kullanılmıyor.
- Işık değişimi plandan geliyor: `flicker` (lamba), `dim_down`, `reveal` (karanlıktan açılma), `lightning`.
- Geçişler varsayılan olarak sert kesme. Zaman atlamasında ("later", "that night", "years") kısa karartma (`fade`) kullanılıyor. Glitch ve flash gibi rastgele efektler yok.
- Ses efekti sahne bazında: boom, hit, creak, knock, static, heartbeat. Hepsi FFmpeg ile sentezleniyor, ücretsiz.

**Ekran yazıları.** Üç ayrı işlev, üç ayrı metin:

| Katman | Ne zaman | Nerede |
|---|---|---|
| Kanca (`hook_text`) | Yalnızca ilk 2,2 sn | Üst güvenli alan, y = 330 px |
| Sahne yazısı (`on_screen_text`) | Yalnızca tarih, yer ya da sayı gerektiğinde, 2,4 sn | Küçük etiket, y = 320 px |
| Altyazı | Anlatım boyunca | y = 1150–1326 px, 80 px; sağda 150 px boşluk (YouTube düğmeleri) |

Kırmızı bant, ortadaki SUBSCRIBE / WATCH NEXT hapları ve sağ alttaki logo planlı modda kapalı. Gerçek vaka dosya kartı yalnızca `gercek_vaka` ailesinde gösteriliyor.

Shorts güvenli alanı (1080x1920) şöyle varsayıldı:
- Üst 290 px: arama ve menü
- Alt 440 px: başlık ve kanal adı
- Sağ 130 px: beğen, yorum ve paylaş düğmeleri

## 3. Örnek üretim planı (antika saat hikâyesi, 3 sahne)

| | Sahne 1 — kanca | Sahne 3 — ipucu | Sahne 6 — dönüm noktası |
|---|---|---|---|
| Anlatım | "The grandfather clock had no internal gears. It struck twelve every midnight anyway." | "The towering walnut case was completely gutted. No pendulum, no chime rods, just empty dark wood." | "When Elena pried the backboard off… fresh fingernail scratches carved from the inside out." |
| Amaç | Çelişkiyle izleyiciyi durdurmak | Saatin gerçekten boş olduğunu kanıtlamak | İçeriden bir şeyin çıkmaya çalıştığını göstermek |
| Ana odak | Gece yarısını gösteren kadran; sarkacın olması gereken boş karanlık | Açık kapağın içindeki boş ahşap kasa | Kasanın iç yüzündeki taze tırnak izleri |
| Duygu | Elena kadrana bakıyor, nefesini tutmuş, bir adım geri | Şaşkınlık: eli kapakta donmuş, gözleri boşlukta | Dehşet: levye elinden düşüyor, geri çekiliyor |
| Ölçek / hareket | close / `push_in` (kadrana yavaş yaklaşma) | extreme_close / `static` (kanıt karesi) | extreme_close / `tilt_down` (izler boyunca aşağı) |
| Işık / renk | Tek gaz lambası, sıcak sarı; arka lacivert-siyah; `flicker` | Lambadan sarı ışık kasanın içine düşüyor; `dim_down` | Soğuk mavi pencere ışığı + sarı lamba; `lightning` |
| Ekran yazısı | Kanca: "IT HAD NO PENDULUM" (başlıktan farklı) | Yok | Yok |
| Devamlılık | Elena: 30'larında, siyah düz saç, koyu yeşil yün palto; saat solda | Aynı palto ve koridor; saat hâlâ solda | Aynı saat, kapağı artık sökülmüş; arka duvar taş |
| Ses | `boom` + saat çanı yok (sessizlik) | `creak` (kapak) | `hit` |
| Görsel ne katıyor | Boş sarkaç boşluğu → "nasıl çalıyor?" sorusu | Ölçek: insan eli boş dev kasanın içinde | Ayrıntı: izler içten dışa, tahta kıymıkları dışarı dönük |

## 4. Kalite kontrolü (yayın öncesi, `kalite_kontrol.py`)

| Madde | Nasıl | Sonuç türü |
|---|---|---|
| Dikey format, codec, süre, ses, siyah kare | FFmpeg ile dosyanın kendisi | Otomatik (GEÇTİ / KALDI) |
| Aynı görsel tekrar edilmiş mi | Sahne planı: her kaynak bir kez | Otomatik (KALDI engeller) |
| Neredeyse aynı görseller | Ortalama hash (8x8), Hamming ≤ 4 | Otomatik (UYARI) |
| Kamera çeşitliliği | Aynı hareket üst üste 3 kez | Otomatik (UYARI) |
| Kanca / başlık / anlatım / sahne yazısı tekrarı | Normalize metin karşılaştırma | Otomatik (KALDI engeller) |
| Kırmızı bant, yazı yoğunluğu | Plan değerleri | Otomatik (UYARI) |
| Altyazı güvenli alanda mı, okunur boyutta mı | Yerleşim değerlerinden hesap (render edilmiş kare ölçülmez) | Otomatik (KALDI engeller) |
| Görselde yazı, bozuk el/yüz, anlatımla uyumsuzluk, karakter tutarsızlığı | Gemini görüntü modeliyle ön-tarama (ücretsiz katman) | En fazla UYARI. Kesin değil, doğrulanmış sayılmaz |
| Bozuk el/yüz/nesne, görsel–ses anlam uyumu | — | **MANUEL**: insan gözüyle bakılır, "geçti" gösterilmez |

MANUEL ve UYARI yayını engellemez. Ama her ikisi de rapora yazılır, paket içindeki `sahneler/` klasöründeki görsellerle birlikte incelenir.

## 5. A/B deney planı (gerçek kanalda uygulamadan önce onay gerekir)

1. **Örnek aşaması (kanala dokunmaz):** `Actions → Gorsel A/B ornegi` aynı hikâye ve aynı ses için A ve B videosu üretir. `gorsel-ab` artefaktında iki paket, sahne görselleri, kalite raporu ve maliyet/süre ölçümü bulunur. Hiçbir şey yüklenmez, hafızaya yazılmaz.
2. **Yayın aşaması (onayınla):** `GORSEL_STIL=AB` repo değişkeni açılırsa günlük üretim stili güne göre dönüşümlü seçer. **Her hikâye tek bir stille** yayınlanır; aynı video iki kez yüklenmez. Her video yine onay kapısından geçer.
3. **Ölçüm:** Haftalık rapordaki "Gorsel stil A/B" bölümü (`kanal_analiz.py`) şunları karşılaştırır:
   - Aynı yayın yaşında (7 gün) izlenme
   - Ortalama izlenme yüzdesi
   - Ortalama izlenme süresi
   - Kazanılan abone

   "İzlemeyi seçenler" (engaged views) oranı API'de yoksa Studio'dan elle bakılır.
4. **Karar kuralı:** Her stilde en az 3 video ve Analytics verisi olmadan kazanan ilan edilmez. Pratikte 4–6 haftalık veri hedeflenir. Hikâye ailesi ve konu farkı gürültü yaratır; fark küçükse karar "fark yok" olur.
5. **Olası etkiler:**
   - B daha az yazı kullandığı için ilk saniyede kaydırma artabilir.
   - Yakın planlar küçük ekranda daha okunur olabilir.
   - Deney süresince kanal görünümü iki stil arasında gidip gelir.
   - Maliyet değişmez: ikisi de video başına ~8 FLUX görseli kullanır. Cloudflare'in ücretsiz günlük 10.000 neuron limiti içinde kalır (~160 neuron/görsel tahmini, kesin değer Cloudflare panelinde).

**Ön koşul:** Analytics metrikleri için token'da `yt-analytics.readonly` yetkisi olmalı. Bunun için `yenile_token.py` çalıştırılmalı ve `TOKEN_JSON` secret'ı güncellenmeli. Bu yapılmadan yalnızca izlenme sayısı karşılaştırılabilir.
