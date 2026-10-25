# -*- coding: utf-8 -*-
"""
KANAL ANALIZI + KENDINI IYILESTIRME DONGUSU

Gunluk:  python kanal_analiz.py --anlik       -> gercek kanal verisini ceker, veri/ altina kaydeder
Haftalik: python kanal_analiz.py --haftalik   -> ayni yayin yasinda karsilastirma raporu yazar ve
                                               veri/icerik_dagilimi.json'u (konu dagilimi) gunceller

Veri kaynaklari (uydurma yok; erisilemeyen metrik raporda "erisilemedi" yazar):
  - YouTube Data API v3 (youtube.readonly): abone/izlenme/video sayisi, her videonun basligi, yayin
    tarihi, suresi, izlenme/begeni/yorum sayisi.
  - YouTube Analytics API v2 (yt-analytics.readonly): izlenme suresi, ortalama izlenme suresi/yuzdesi,
    kazanilan abone, trafik kaynaklari, video bazinda gunluk izlenme (ayni yasta karsilastirma icin).
    Token'da bu yetki yoksa bu bolum atlanir ve raporda nasil acilacagi yazar.
  - YouTube Studio'ya ozel (API'de yok): para kazanma uygunlugu, Shorts "izlemeyi secenler/kaydirip
    gecenler" orani. Bunlar raporda STUDIO etiketiyle ayri belirtilir, hesaplanmaz.
"""
import argparse
import datetime
import json
import os
import re
import statistics
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VERI = os.path.join(BASE_DIR, "veri")
TOKEN_FILE = os.path.join(BASE_DIR, "token.json")
ANALIZ_SCOPE = "https://www.googleapis.com/auth/yt-analytics.readonly"
AILELER = ("gercek_vaka", "hayatta_kalma", "ozgun_korku")
YAS_HEDEFLERI = (1, 3, 7, 28)        # ayni yasta karsilastirma noktalari (gun)
MIN_ORNEK = 3                        # bir aile icin karar vermeden once gereken en az video
MAX_HAFTALIK_DEGISIM = 0.15          # dagilim bir haftada en fazla bu kadar oynar
SINIR = (0.15, 0.60)                 # her ailenin pay alt/ust siniri


# ------------------------------------------------------------------ saf yardimcilar (test edilir)
def iso_sure_sn(iso):
    """'PT1M5S' -> 65"""
    m = re.fullmatch(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso or "")
    if not m:
        return 0
    g, s, d, sn = (int(x or 0) for x in m.groups())
    return g * 86400 + s * 3600 + d * 60 + sn


def yas_gun(yayin_iso, simdi=None):
    simdi = simdi or datetime.datetime.now(datetime.timezone.utc)
    yayin = datetime.datetime.fromisoformat(yayin_iso.replace("Z", "+00:00"))
    return (simdi - yayin).total_seconds() / 86400


def sure_kovasi(sn):
    if sn < 30:
        return "<30 sn"
    if sn < 45:
        return "30-45 sn"
    if sn <= 60:
        return "45-60 sn"
    return ">60 sn"


def yasa_gore_izlenme(gunluk, yas):
    """gunluk: [(gun_index, izlenme)] (0 = yayin gunu) -> ilk `yas` gundeki toplam izlenme."""
    return sum(v for g, v in gunluk if g < yas)


def agirlik_guncelle(onceki, skorlar, sayilar):
    """
    Aile paylarini performansa gore yumusakca gunceller.
      skorlar: {aile: ayni-yas medyan izlenme}, sayilar: {aile: ornek sayisi}
    - MIN_ORNEK'ten az veri olan ailenin payi DEGISMEZ (az veriyle karar yok)
    - skor, genel medyana dogru 'buzulur' (k=5) -> tek viral video stratejiyi devirmez
    - haftalik degisim +-MAX_HAFTALIK_DEGISIM ile, paylar SINIR ile sinirli
    """
    onceki = {a: float(onceki.get(a, 1 / len(AILELER))) for a in AILELER}
    gecerli = {a: s for a, s in skorlar.items() if sayilar.get(a, 0) >= MIN_ORNEK and s is not None}
    if len(gecerli) < 2:
        return dict(onceki), "yeterli veri yok: dagilim degismedi"
    genel = statistics.median(gecerli.values()) or 1.0
    k = 5
    hedef = {}
    for a in AILELER:
        if a in gecerli:
            n = sayilar[a]
            buzulmus = (n * gecerli[a] + k * genel) / (n + k)
            hedef[a] = onceki[a] * (buzulmus / genel)
        else:
            hedef[a] = onceki[a]
    toplam = sum(hedef.values())
    hedef = {a: v / toplam for a, v in hedef.items()}
    # Degisimleri toplami SIFIR olacak sekilde sinirla (toplam pay hep 1 kalir): her ailenin
    # degisimi +-MAX_HAFTALIK_DEGISIM icinde ve sonuc SINIR araliginda olacak sekilde izdusum.
    d = {a: hedef[a] - onceki[a] for a in AILELER}
    for _ in range(100):
        alt = {a: max(-MAX_HAFTALIK_DEGISIM, SINIR[0] - onceki[a]) for a in AILELER}
        ust = {a: min(MAX_HAFTALIK_DEGISIM, SINIR[1] - onceki[a]) for a in AILELER}
        d = {a: min(ust[a], max(alt[a], d[a])) for a in AILELER}
        artik = sum(d.values())
        if abs(artik) < 1e-9:
            break
        # fazlayi/eksigi hala hareket payi olan ailelere esit dagit
        oynayabilir = [a for a in AILELER if (artik > 0 and d[a] > alt[a] + 1e-12) or (artik < 0 and d[a] < ust[a] - 1e-12)]
        if not oynayabilir:
            break
        for a in oynayabilir:
            d[a] -= artik / len(oynayabilir)
    yeni = {a: onceki[a] + d[a] for a in AILELER}
    yeni = {a: round(v, 3) for a, v in yeni.items()}
    return yeni, "performansa gore guncellendi (buzulmus medyan, haftalik sinirli degisim)"


# ------------------------------------------------------------------ API
def _kimlik():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    if not os.path.exists(TOKEN_FILE):
        raise SystemExit("token.json yok: YouTube verisi cekilemez (GitHub'da TOKEN_JSON secret'i gerekli).")
    creds = Credentials.from_authorized_user_file(TOKEN_FILE)
    if not creds.valid and creds.refresh_token:
        creds.refresh(Request())
    return creds


def data_api_cek(yt, en_fazla=500):
    kanal = yt.channels().list(part="snippet,statistics,contentDetails", mine=True).execute()["items"][0]
    st = kanal["statistics"]
    ozet = {
        "kanal_adi": kanal["snippet"]["title"],
        "abone": None if st.get("hiddenSubscriberCount") else int(st.get("subscriberCount", 0)),
        "toplam_izlenme": int(st.get("viewCount", 0)),
        "video_sayisi": int(st.get("videoCount", 0)),
    }
    yuklemeler = kanal["contentDetails"]["relatedPlaylists"]["uploads"]
    idler, sayfa = [], None
    while len(idler) < en_fazla:
        r = yt.playlistItems().list(part="contentDetails", playlistId=yuklemeler, maxResults=50,
                                    pageToken=sayfa).execute()
        idler += [i["contentDetails"]["videoId"] for i in r.get("items", [])]
        sayfa = r.get("nextPageToken")
        if not sayfa:
            break
    videolar = []
    for i in range(0, len(idler), 50):
        r = yt.videos().list(part="snippet,statistics,contentDetails,status", id=",".join(idler[i:i + 50])).execute()
        for v in r.get("items", []):
            s = v.get("statistics", {})
            videolar.append({
                "video_id": v["id"],
                "baslik": v["snippet"]["title"],
                "yayin": v["snippet"]["publishedAt"],
                "sure_sn": iso_sure_sn(v["contentDetails"].get("duration")),
                "gizlilik": v.get("status", {}).get("privacyStatus"),
                "izlenme": int(s.get("viewCount", 0) or 0),
                "begeni": int(s.get("likeCount", 0) or 0),
                "yorum": int(s.get("commentCount", 0) or 0),
            })
    return ozet, videolar


def analytics_cek(creds, videolar):
    """Analytics API. Yetki yoksa {'erisim': False, 'neden': ...} doner."""
    if ANALIZ_SCOPE not in set(creds.scopes or []):
        return {"erisim": False, "neden": "token'da yt-analytics.readonly yetkisi yok "
                                          "(yenile_token.py ile token'i yenileyip TOKEN_JSON'u guncelleyin)"}
    from googleapiclient.discovery import build
    ya = build("youtubeAnalytics", "v2", credentials=creds, cache_discovery=False)
    bugun = datetime.date.today()
    sonuc = {"erisim": True, "donemler": {}, "video": {}, "trafik": [], "eksik_metrikler": []}

    def sorgu(**kw):
        return ya.reports().query(ids="channel==MINE", **kw).execute()

    for gun in (7, 28, 90):
        bas = (bugun - datetime.timedelta(days=gun)).isoformat()
        try:
            r = sorgu(startDate=bas, endDate=bugun.isoformat(),
                      metrics="views,estimatedMinutesWatched,averageViewDuration,averageViewPercentage,"
                              "subscribersGained,subscribersLost")
            basliklar = [c["name"] for c in r["columnHeaders"]]
            satir = (r.get("rows") or [[0] * len(basliklar)])[0]
            sonuc["donemler"][f"son_{gun}_gun"] = dict(zip(basliklar, satir))
        except Exception as e:
            sonuc["donemler"][f"son_{gun}_gun"] = {"hata": str(e)[:160]}
    # Shorts'a ozel metrik API'de olmayabilir: denenir, yoksa eksik olarak raporlanir
    try:
        r = sorgu(startDate=(bugun - datetime.timedelta(days=28)).isoformat(), endDate=bugun.isoformat(),
                  metrics="engagedViews")
        sonuc["donemler"]["son_28_gun"]["engagedViews"] = (r.get("rows") or [[None]])[0][0]
    except Exception:
        sonuc["eksik_metrikler"].append("engagedViews (Shorts izlemeyi secenler) - API'de erisilemedi, Studio'dan bakin")
    try:
        r = sorgu(startDate=(bugun - datetime.timedelta(days=90)).isoformat(), endDate=bugun.isoformat(),
                  dimensions="video", sort="-views", maxResults=200,
                  metrics="views,estimatedMinutesWatched,averageViewDuration,averageViewPercentage,subscribersGained")
        basliklar = [c["name"] for c in r["columnHeaders"]]
        for satir in r.get("rows") or []:
            d = dict(zip(basliklar, satir))
            sonuc["video"][d.pop("video")] = d
    except Exception as e:
        sonuc["video_hata"] = str(e)[:160]
    try:
        r = sorgu(startDate=(bugun - datetime.timedelta(days=28)).isoformat(), endDate=bugun.isoformat(),
                  dimensions="insightTrafficSourceType", metrics="views", sort="-views")
        sonuc["trafik"] = [{"kaynak": a, "izlenme": b} for a, b in (r.get("rows") or [])]
    except Exception as e:
        sonuc["trafik_hata"] = str(e)[:160]
    # ayni yasta karsilastirma: son 120 gunde yayinlanan videolarin gunluk izlenmesi
    sonuc["gunluk"] = {}
    for v in videolar:
        if yas_gun(v["yayin"]) > 120:
            continue
        yayin_gunu = v["yayin"][:10]
        try:
            r = sorgu(startDate=yayin_gunu, endDate=bugun.isoformat(), dimensions="day",
                      metrics="views", filters=f"video=={v['video_id']}")
            g0 = datetime.date.fromisoformat(yayin_gunu)
            sonuc["gunluk"][v["video_id"]] = [((datetime.date.fromisoformat(d) - g0).days, int(n))
                                             for d, n in (r.get("rows") or [])]
        except Exception:
            continue
    return sonuc


# ------------------------------------------------------------------ aile eslestirme
def aile_eslestir(videolar):
    """video_id/baslik -> aile/topic_type (veri/videolar.json + gecmis.json)."""
    eslesme = {}
    for yol, anahtar in ((os.path.join(VERI, "videolar.json"), "videolar"), (os.path.join(BASE_DIR, "gecmis.json"), "videolar")):
        try:
            with open(yol, encoding="utf-8") as f:
                for k in json.load(f).get(anahtar, []):
                    bilgi = {"aile": k.get("aile") or "", "topic_type": k.get("topic_type") or ""}
                    if k.get("video_id"):
                        eslesme.setdefault(k["video_id"], bilgi)
                    for b in (k.get("baslik"), k.get("title")):
                        if b:
                            eslesme.setdefault("t:" + re.sub(r"\W+", "", b.lower()), bilgi)
        except Exception:
            continue
    for v in videolar:
        bilgi = eslesme.get(v["video_id"]) or eslesme.get("t:" + re.sub(r"\W+", "", v["baslik"].lower())) or {}
        # Strateji oncesi videolar (aile alani yok) 'eski_format' grubunda tutulur
        v["aile"] = bilgi.get("aile") or "eski_format"
        v["topic_type"] = bilgi.get("topic_type") or ""
    return videolar


# ------------------------------------------------------------------ komutlar
def anlik():
    from googleapiclient.discovery import build
    creds = _kimlik()
    yt = build("youtube", "v3", credentials=creds, cache_discovery=False)
    ozet, videolar = data_api_cek(yt)
    analiz = analytics_cek(creds, videolar)
    videolar = aile_eslestir(videolar)
    bugun = datetime.date.today().isoformat()
    kayit = {"tarih": bugun, "kanal": ozet, "videolar": videolar, "analytics": analiz}
    os.makedirs(os.path.join(VERI, "istatistik"), exist_ok=True)
    with open(os.path.join(VERI, "istatistik", f"{bugun}.json"), "w", encoding="utf-8") as f:
        json.dump(kayit, f, ensure_ascii=False, indent=1)
    with open(os.path.join(VERI, "kanal_son.json"), "w", encoding="utf-8") as f:
        json.dump(kayit, f, ensure_ascii=False, indent=1)
    print(f"Kanal: {ozet['kanal_adi']} | abone {ozet['abone']} | toplam izlenme {ozet['toplam_izlenme']:,} "
          f"| video {ozet['video_sayisi']}")
    print("Analytics:", "erisildi" if analiz.get("erisim") else "ERISILEMEDI - " + analiz.get("neden", ""))
    return kayit


def _yas_esli_skor(v, gunluk, yas=7):
    """Videonun ilk `yas` gundeki izlenmesi. Gunluk veri yoksa ve video bu yasi gecmisse None
    (toplam izlenme farkli yasta oldugu icin karsilastirmaya katilmaz)."""
    if v["video_id"] in gunluk:
        if yas_gun(v["yayin"]) >= yas:
            return yasa_gore_izlenme(gunluk[v["video_id"]], yas)
        return None
    return None


def haftalik():
    yol = os.path.join(VERI, "kanal_son.json")
    if not os.path.exists(yol):
        kayit = anlik()
    else:
        with open(yol, encoding="utf-8") as f:
            kayit = json.load(f)
    videolar = [v for v in kayit["videolar"] if v.get("gizlilik") in (None, "public")]
    an = kayit.get("analytics") or {}
    gunluk = {k: [tuple(x) for x in v] for k, v in (an.get("gunluk") or {}).items()}

    satirlar = [f"# Haftalik kanal raporu - {kayit['tarih']}", ""]
    k = kayit["kanal"]
    satirlar += ["## Kanal (YouTube Data API - dogrulanmis)",
                 f"- Kanal: {k['kanal_adi']}", f"- Abone: {k['abone']}",
                 f"- Toplam izlenme: {k['toplam_izlenme']:,}", f"- Video sayisi: {k['video_sayisi']}", ""]
    satirlar.append("## Donemsel performans (YouTube Analytics API)")
    if an.get("erisim"):
        for d, m in an.get("donemler", {}).items():
            satirlar.append(f"- {d}: " + ", ".join(f"{a}={b}" for a, b in m.items()))
        if an.get("trafik"):
            satirlar.append("- Trafik kaynaklari (28 gun): " + ", ".join(f"{t['kaynak']}={t['izlenme']}" for t in an["trafik"][:6]))
        for e in an.get("eksik_metrikler", []):
            satirlar.append(f"- ERISILEMEDI: {e}")
    else:
        satirlar.append(f"- ERISILEMEDI: {an.get('neden', 'bilinmiyor')}")
    satirlar += ["- STUDIO'YA OZEL (API'de yok, hesaplanmadi): para kazanma uygunlugu / YPP ilerlemesi, "
                 "Shorts 'izlemeyi secenler vs kaydirip gecenler' orani.", ""]

    # Aile bazinda ayni-yas (7 gun) karsilastirma
    satirlar.append("## Icerik ailesi karsilastirmasi (ayni yayin yasinda: ilk 7 gun izlenme)")
    skorlar, sayilar = {}, {}
    gruplar = {}
    for v in videolar:
        skor = _yas_esli_skor(v, gunluk, 7)
        if skor is not None:
            gruplar.setdefault(v["aile"], []).append(skor)
    if not gruplar:
        satirlar.append("- Ayni yasta karsilastirilabilir veri yok (Analytics gunluk izlenme gerekli "
                        "ve yeni stratejinin videolari en az 7 gunluk olmali).")
    for aile, liste in sorted(gruplar.items()):
        skorlar[aile] = statistics.median(liste)
        sayilar[aile] = len(liste)
        satirlar.append(f"- {aile}: {len(liste)} video, medyan {skorlar[aile]:.0f} izlenme"
                        + ("" if len(liste) >= MIN_ORNEK else "  (az veri - karar verilmedi)"))
    satirlar.append("")

    satirlar.append("## Sure kovalarina gore (Analytics ortalama izlenme yuzdesi)")
    vid_an = an.get("video") or {}
    kovalar = {}
    for v in videolar:
        m = vid_an.get(v["video_id"])
        if m and m.get("averageViewPercentage") is not None:
            kovalar.setdefault(sure_kovasi(v["sure_sn"]), []).append(m["averageViewPercentage"])
    if kovalar:
        for kv, l in sorted(kovalar.items()):
            satirlar.append(f"- {kv}: {len(l)} video, medyan izlenme yuzdesi %{statistics.median(l):.0f}")
    else:
        satirlar.append("- Veri yok (Analytics erisimi gerekli).")
    satirlar.append("")

    # En iyi / en zayif (yalnizca 7+ gunluk videolar, ayni yasta)
    olgun = [(v, _yas_esli_skor(v, gunluk, 7)) for v in videolar]
    olgun = [(v, s) for v, s in olgun if s is not None]
    if olgun:
        olgun.sort(key=lambda x: x[1], reverse=True)
        satirlar.append("## En iyi 5 (ilk 7 gun)")
        satirlar += [f"- {s} | {v['baslik']} ({v['aile']}, {v['sure_sn']} sn)" for v, s in olgun[:5]]
        satirlar.append("## En zayif 5 (ilk 7 gun)")
        satirlar += [f"- {s} | {v['baslik']} ({v['aile']}, {v['sure_sn']} sn)" for v, s in olgun[-5:]]
        satirlar.append("")

    # Dagilim guncelle
    dag_yol = os.path.join(VERI, "icerik_dagilimi.json")
    try:
        with open(dag_yol, encoding="utf-8") as f:
            onceki = json.load(f).get("agirliklar", {})
    except Exception:
        onceki = {}
    yeni, neden = agirlik_guncelle(onceki, {a: skorlar.get(a) for a in AILELER},
                                   {a: sayilar.get(a, 0) for a in AILELER})
    with open(dag_yol, "w", encoding="utf-8") as f:
        json.dump({"guncelleme": kayit["tarih"], "agirliklar": yeni, "neden": neden,
                   "onceki": onceki}, f, ensure_ascii=False, indent=1)
    satirlar += ["## Gelecek haftanin konu dagilimi", f"- {neden}"]
    satirlar += [f"- {a}: %{yeni[a] * 100:.0f} (onceki %{float(onceki.get(a, 1 / 3)) * 100:.0f})" for a in AILELER]
    rapor = "\n".join(satirlar) + "\n"
    with open(os.path.join(VERI, "haftalik_rapor.md"), "w", encoding="utf-8") as f:
        f.write(rapor)
    print(rapor)
    return rapor


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--anlik", action="store_true")
    ap.add_argument("--haftalik", action="store_true")
    a = ap.parse_args()
    if a.anlik:
        anlik()
    if a.haftalik:
        haftalik()
    if not (a.anlik or a.haftalik):
        ap.print_help()
        sys.exit(2)
