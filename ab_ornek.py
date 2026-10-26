# -*- coding: utf-8 -*-
"""
GORSEL A/B ORNEGI: ayni hikaye + ayni seslendirme, iki gorsel yaklasim.

  A = mevcut cizgi dilinin iyilestirilmisi (yonetmen plani, net odak, kontrollu isik)
  B = daha sinematik isik, ana nesne daha yakin, daha az ekran yazisi

Her iki video da cikti/ab/A ve cikti/ab/B altina paketlenir (video, thumbnail, sahne gorselleri,
meta.json + kalite raporu). HICBIR SEY YAYINLANMAZ ve konu hafizaya yazilmaz; bu yalnizca
gorsel karsilastirma icindir. Yayin sonrasi gercek olcum, stillerin FARKLI hikayelerde
donusumlu kullanilmasiyla yapilir (ayni video iki kez yuklenmez) - bkz. docs/gorsel_yonetmenlik.md

Kullanim:  python ab_ornek.py            (Gemini + Cloudflare anahtarlari gerekir)
"""
import json
import os
import shutil
import sys
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

import kalite_kontrol as kk  # noqa: E402
import shorts_otomasyon as so  # noqa: E402

AB_KLASORU = os.path.join(BASE_DIR, "cikti", "ab")
# Cloudflare Workers AI ucretsiz katmani: gunluk 10.000 neuron. flux-2-klein-4b 864x1536 ~160 neuron/gorsel
# (Cloudflare panelindeki kullanim degerinden; kesin fiyat icin panel esas alinir).
NEURON_GORSEL = 160


def _b_varyanti(data):
    """B: ana nesne daha yakin, ekran yazisi yalnizca kanca (uretimdeki kural: so.b_plani)."""
    return so.b_plani(json.loads(json.dumps({k: v for k, v in data.items() if not k.startswith("_")})))


def varyant_uret(stil, data, words, baslik, aciklama, etiketler, thumb_yazi, script):
    klasor = os.path.join(AB_KLASORU, stil)
    shutil.rmtree(klasor, ignore_errors=True)
    os.makedirs(klasor, exist_ok=True)
    bas = time.time()
    medya = so.flux_sahneleri(data, [], stil=stil, klasor=os.path.join(so.MEDYA_KLASORU + "_" + stil))
    gorsel_sn = time.time() - bas
    if len(medya) < so.ANIM_MIN_GORSEL:
        print(f"  [{stil}] yeterli gorsel yok ({len(medya)}), atlandi")
        return None
    video = os.path.join(klasor, "video.mp4")
    bas = time.time()
    so.remotion_olustur(words, medya, data, thumb_yazi, video, cizgi=True)
    render_sn = time.time() - bas
    thumb = None
    try:
        thumb = so.thumbnail_olustur(medya, thumb_yazi or baslik, os.path.join(klasor, "thumbnail.jpg"), video)
    except Exception as e:
        print("  (thumbnail uretilemedi:", str(e)[:100], ")")
    sahne_klasoru = os.path.join(klasor, "sahneler")
    os.makedirs(sahne_klasoru, exist_ok=True)
    for yol, _ in data.get("_sahne_medya") or []:
        shutil.copyfile(yol, os.path.join(sahne_klasoru, os.path.basename(yol)))
    meta = {
        "varyant": stil, "aile": data.get("aile"), "konu": data.get("topic"),
        "baslik": baslik, "aciklama": aciklama, "etiketler": etiketler, "script": script,
        "kaynak": data.get("kaynak") or {}, "gorsel_motoru": "cloudflare-flux", "gorsel_stil": stil,
        "medya_kaynagi": ["cloudflare-flux", so.SON_SES_MOTORU, "sentetik-ses"],
        "gorsel_sayisi": len(medya), "kanca_yazisi": (data.get("_ekran_plani") or {}).get("kanca", ""),
        "maliyet": {"usd": 0.0, "tahmini_neuron": len(medya) * NEURON_GORSEL,
                    "not": "Cloudflare ucretsiz gunluk 10.000 neuron icinde"},
        "sure_olcumu_sn": {"gorsel": round(gorsel_sn, 1), "render": round(render_sn, 1)},
        "ekran_plani": so._ekran_plani_ozeti(data, baslik, script),
        "gorsel_tarama": so.gorsel_on_tarama(data),
    }
    print(f"[QC {stil}]")
    sonuc = kk.kontrol_et(video, meta, gorsel_klasoru=sahne_klasoru)
    kk.ozet_yazdir(sonuc)
    meta["kalite"] = sonuc
    meta["sure_sn"] = round(kk.video_bilgisi(video)["sure"] or 0, 2)
    with open(os.path.join(klasor, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=1)
    return meta


def main():
    if not so.cf_hazir():
        raise SystemExit("Cloudflare anahtarlari yok (CLOUDFLARE_ACCOUNT_ID / CLOUDFLARE_API_TOKEN).")
    print("[1/3] Hikaye + yonetmen plani (Gemini)...")
    data = so.gemini_uret(None, [])
    script, baslik = data["script"], data["title"]
    baslik, aciklama, etiketler = so._seo_duzenle(baslik, data["description"], data.get("tags", []),
                                                  data.get("topic", ""), data.get("aile", "gercek_vaka"))
    aciklama = so.aciklama_son_hali(aciklama, data.get("aile"), data.get("kaynak") or {}, "cloudflare-flux")
    thumb_yazi = (data.get("thumbnail_text") or "").strip()
    print(f"      Konu: {data.get('topic')} | Kanca: {data.get('hook_text')}")
    print("[2/3] Seslendirme (her iki varyant ayni ses)...")
    words, _ = so.seslendir(script, so.AUDIO_FILE)
    sonuclar = {}
    for stil, veri in (("A", data), ("B", _b_varyanti(data))):
        print(f"[3/3] Varyant {stil} ...")
        so.GORSEL_STIL = stil
        sonuclar[stil] = varyant_uret(stil, veri, words, baslik, aciklama, etiketler, thumb_yazi, script)
    ozet = {s: (None if m is None else {"kalite_gecti": m["kalite"]["gecti"], "gorsel": m["gorsel_sayisi"],
                                         "neuron": m["maliyet"]["tahmini_neuron"], "sure_sn": m["sure_sn"],
                                         "olcum_sn": m["sure_olcumu_sn"],
                                         "tarama_bulgusu": len((m.get("gorsel_tarama") or {}).get("bulgular") or [])})
            for s, m in sonuclar.items()}
    with open(os.path.join(AB_KLASORU, "ozet.json"), "w", encoding="utf-8") as f:
        json.dump({"konu": data.get("topic"), "script": script, "varyantlar": ozet}, f, ensure_ascii=False, indent=1)
    print("A/B OZET:", json.dumps(ozet, ensure_ascii=False))
    print("Hicbir sey yayinlanmadi. Paketler:", AB_KLASORU)


if __name__ == "__main__":
    main()
