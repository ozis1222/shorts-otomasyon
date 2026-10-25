# -*- coding: utf-8 -*-
"""
ONAYLI YAYIN: uretilmis bir yayin paketini YouTube'a yukler.

Uretim (shorts_otomasyon.py) varsayilan olarak hicbir sey yayinlamaz; videoyu, thumbnail'i ve
meta.json'u bir pakete koyar. Kullanici paketi inceleyip onaylayinca bu arac calisir
(GitHub'da: Actions > "Yayinla (onayli)" > Run workflow > uretim kosusunun run_id'si).

Guvenlik kurallari:
  - kalite kontrolunden GECMEMIS paket yuklenmez
  - ayni paket ikinci kez yuklenmez (veri/videolar.json'da video_id varsa durur)
  - --deneme ile hicbir sey yuklemeden ne yapilacagini gosterir

Kullanim:
  python yayinla.py --paket cikti/paket --gizlilik public
  python yayinla.py --paket cikti/paket --deneme
"""
import argparse
import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)


def paketi_oku(klasor):
    meta_yolu = os.path.join(klasor, "meta.json")
    video = os.path.join(klasor, "video.mp4")
    if not os.path.exists(meta_yolu) or not os.path.exists(video):
        raise SystemExit(f"HATA: paket eksik ({klasor}): meta.json ve video.mp4 gerekli.")
    with open(meta_yolu, encoding="utf-8") as f:
        return json.load(f), video


def daha_once_yuklendi_mi(paket_id, videolar_dosyasi):
    try:
        with open(videolar_dosyasi, encoding="utf-8") as f:
            kayitlar = json.load(f).get("videolar", [])
    except Exception:
        return ""
    for k in kayitlar:
        if k.get("paket_id") == paket_id and k.get("video_id"):
            return k["video_id"]
    return ""


def main(argv=None):
    ap = argparse.ArgumentParser(description="Onaylanan yayin paketini YouTube'a yukler")
    ap.add_argument("--paket", default=os.path.join(BASE_DIR, "cikti", "paket"))
    ap.add_argument("--gizlilik", choices=["public", "unlisted", "private"], default="public")
    ap.add_argument("--deneme", action="store_true", help="yukleme yapmadan kontrol et")
    a = ap.parse_args(argv)

    meta, video = paketi_oku(a.paket)
    print(f"Paket   : {meta['paket_id']}  ({meta.get('aile')})")
    print(f"Baslik  : {meta['baslik']}")
    print(f"Sure    : {meta.get('sure_sn')} sn   Gorsel: {meta.get('gorsel_motoru')}")

    if not meta.get("kalite", {}).get("gecti"):
        kalanlar = [k["kontrol"] for k in meta.get("kalite", {}).get("kontroller", []) if k["durum"] == "KALDI"]
        raise SystemExit(f"DURDU: paket kalite kontrolunden gecmemis -> {kalanlar}. Yuklenmedi.")

    import shorts_otomasyon as so
    import kalite_kontrol as kk
    # Eski paketler icin: kurgu hikayeden gercek-olay etiketlerini at, icerik kontrolunu yeniden calistir
    if meta.get("aile") in ("hayatta_kalma", "ozgun_korku"):
        temiz = [e for e in meta.get("etiketler", []) if not any(g in str(e).lower() for g in so._GERCEK_GIBI)]
        if len(temiz) != len(meta.get("etiketler", [])):
            print(f"Etiket  : kurguya uymayan {len(meta['etiketler']) - len(temiz)} etiket cikarildi")
            meta["etiketler"] = temiz + [e for e in so.SEO_KURGU_ETIKET if e not in temiz][:15 - len(temiz)]
    icerik = kk.icerik_kontrol(meta)
    kalan = [k["kontrol"] for k in icerik if k["durum"] == "KALDI"]
    if kalan:
        raise SystemExit(f"DURDU: yayin aninda icerik kontrolu kaldi -> {kalan}. Yuklenmedi.")

    onceki = daha_once_yuklendi_mi(meta["paket_id"], so.VIDEOLAR_FILE)
    if onceki:
        raise SystemExit(f"DURDU: bu paket zaten yuklenmis (https://youtu.be/{onceki}). Cift yayin engellendi.")

    if a.deneme:
        print(f"DENEME: '{a.gizlilik}' olarak yuklenecekti. Hicbir sey yuklenmedi.")
        return 0

    so.PRIVACY = a.gizlilik
    thumb = os.path.join(a.paket, "thumbnail.jpg")
    video_id = so.youtube_yukle(video, meta["baslik"], meta["aciklama"], meta.get("etiketler", []),
                                thumb if os.path.exists(thumb) else None)
    if not video_id:
        raise SystemExit("HATA: YouTube video kimligi donmedi.")
    # Kayit yoksa (paket baska bir dalda uretildiyse) ekle, varsa guncelle
    kayitlar = so._json_oku(so.VIDEOLAR_FILE, {"videolar": []})
    if not any(k.get("paket_id") == meta["paket_id"] for k in kayitlar.get("videolar", [])):
        so.video_kaydi_ekle({"paket_id": meta["paket_id"], "olusturma": meta.get("olusturma"),
                             "aile": meta.get("aile"), "konu": meta.get("konu"), "baslik": meta["baslik"],
                             "sure_sn": meta.get("sure_sn"), "gorsel_motoru": meta.get("gorsel_motoru"),
                             "maliyet_usd": meta.get("maliyet_usd", 0.0), "kalite_gecti": True})
    import datetime
    so.video_kaydi_guncelle(meta["paket_id"], video_id=video_id, durum="yayinlandi", gizlilik=a.gizlilik,
                            yayin_tarihi=datetime.datetime.now(datetime.timezone.utc).isoformat())
    print(f"YAYINLANDI: https://youtu.be/{video_id}  ({a.gizlilik})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
