# -*- coding: utf-8 -*-
"""
VAR OLAN BIR PAKETI YENIDEN URET: ayni hikaye, ayni baslik/aciklama, ayni sahne gorselleri;
yeniden seslendirme (Kokoro) + guncel kurgu (2.5D paralaks, ortam efektleri) + kalite kontrolu.

Yeni gorsel URETMEZ (FLUX kotasi harcanmaz) ve konu hafizasina yeni kayit eklemez. Cikti yine
cikti/paket altindaki yayin paketidir; yayin ayrica "Yayinla (onayli)" ile yapilir.

Kullanim:  python yeniden_uret.py --kaynak cikti/kaynak_paket
"""
import argparse
import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

import shorts_otomasyon as so  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser(description="Paketi yeni ses + guncel kurguyla yeniden uretir")
    ap.add_argument("--kaynak", default=os.path.join(BASE_DIR, "cikti", "kaynak_paket"))
    a = ap.parse_args(argv)

    with open(os.path.join(a.kaynak, "meta.json"), encoding="utf-8") as f:
        m = json.load(f)
    gorsel_klasoru = os.path.join(a.kaynak, "sahneler")
    gorseller = sorted(g for g in os.listdir(gorsel_klasoru) if g.lower().endswith((".jpg", ".png")))
    planlar = m.get("sahne_plani") or []
    tarifler = m.get("sahne_tarifleri") or []
    if not gorseller or len(gorseller) != len(planlar):
        raise SystemExit(f"HATA: {len(gorseller)} gorsel / {len(planlar)} sahne plani - eslesmiyor, yeniden uretilemez.")
    print(f"Kaynak paket: {m['paket_id']} | {m['baslik']}")

    print("[1/3] Seslendirme...")
    words, motor = so.seslendir(m["script"], so.AUDIO_FILE)
    print(f"      {len(words)} kelime ({motor})")

    eslesme = [(os.path.join(gorsel_klasoru, g), dict(p or {}, image_prompt=t))
               for g, p, t in zip(gorseller, planlar, tarifler + [""] * len(gorseller))]
    data = {"title": m["baslik"], "script": m["script"], "hook_text": m.get("kanca_yazisi", ""),
            "aile": m.get("aile"), "look_bible": m.get("look_bible", ""), "keywords": [],
            "scenes": [p for _, p in eslesme], "_sahne_medya": eslesme}

    print("[2/3] Kurgu (Remotion, paralaks)...")
    medya = [(y, "foto") for y, _ in eslesme]
    so.remotion_olustur(words, medya, data, "", so.OUTPUT_FILE, cizgi=True)
    thumb = os.path.join(a.kaynak, "thumbnail.jpg")
    if not os.path.exists(thumb):
        thumb = so.thumbnail_olustur(medya, m.get("kanca_yazisi") or m["baslik"], so.THUMB_FILE, so.OUTPUT_FILE)

    print("[3/3] Paket + kalite kontrolu...")
    paket = so.yayin_paketi_hazirla(
        baslik=m["baslik"], aciklama=m["aciklama"], etiketler=m.get("etiketler", []), thumb=thumb,
        aile=m.get("aile"), konu=m.get("konu"), topic_type=m.get("topic_type", ""), script=m["script"],
        kaynak=m.get("kaynak") or {}, motor="cloudflare-flux", sahneler=tarifler,
        notlar=[f"yeniden uretildi: {m['paket_id']} (ses: {motor})"], data=data)
    # eski paket yerine yenisi gecti: eski kayit yayin listesinde beklemesin
    so.video_kaydi_guncelle(m["paket_id"], durum="yeniden_uretildi", yerine=paket["meta"]["paket_id"])
    if not paket["meta"]["kalite"]["gecti"]:
        raise SystemExit("Kalite kontrolunden GECMEDI - paket yayinlanamaz.")
    print("Hazir:", paket["klasor"], "| yeni paket:", paket["meta"]["paket_id"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
