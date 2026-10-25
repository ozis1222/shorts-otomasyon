# -*- coding: utf-8 -*-
"""Yonetmen plani: sahne zamanlama, ekran yazilari, gorsel kalite kontrolu."""
import shorts_otomasyon as so
import kalite_kontrol as kk


def _kelimeler(metin, adim=0.4):
    return [{"word": w, "start": i * adim, "end": i * adim + 0.35} for i, w in enumerate(metin.split())]


METIN = ("The clock had no gears. It struck twelve anyway. Elena moved in during winter. "
         "She placed a microphone inside. The tape caught two voices. Then the scratches appeared.")
PARCALAR = ["The clock had no gears. It struck twelve anyway.", "Elena moved in during winter.",
            "She placed a microphone inside.", "The tape caught two voices.", "Then the scratches appeared."]


def test_sahneler_anlatim_parcasinda_baslar_ve_tekrar_etmez():
    words = _kelimeler(METIN)
    planlar = [{"narration": p, "move": "push_in"} for p in PARCALAR]
    eslesme = [(f"run/g{i}.jpg", p) for i, p in enumerate(planlar)]
    sahneler = so.planli_sahneler(eslesme, words, words[-1]["end"] + 0.3)
    assert [s["src"] for s in sahneler] == [f"run/g{i}.jpg" for i in range(5)]   # her gorsel bir kez, sirayla
    # 2. sahne "Elena" kelimesinde baslar (9. kelime)
    assert abs(sahneler[1]["start"] - (words[9]["start"] - 0.08)) < 0.01
    kameralar = [s["camera"] for s in sahneler]
    assert not any(kameralar[i] == kameralar[i + 1] == kameralar[i + 2] for i in range(len(kameralar) - 2))
    assert all(s["transition"] in ("cut", "fade") for s in sahneler)


def test_anlatim_bulunamazsa_beklenen_konum_kullanilir():
    words = _kelimeler(METIN)
    planlar = [{"narration": PARCALAR[0]}, {"narration": "completely different words here"}, {"narration": ""}]
    baslar = so.anlatim_baslangiclari(planlar, words)
    assert baslar[0] == 0 and baslar[0] < baslar[1] < baslar[2] < len(words)


def test_cok_kisa_sahne_birlestirilir():
    words = _kelimeler(METIN)
    planlar = [{"narration": "The clock had no gears."}, {"narration": "It struck"},
               {"narration": "twelve anyway. Elena moved in during winter."}]
    sahneler = so.planli_sahneler([(f"g{i}", p) for i, p in enumerate(planlar)], words, words[-1]["end"])
    assert all(b["start"] - a["start"] >= so._MIN_SAHNE_SN for a, b in zip(sahneler, sahneler[1:]))


def test_ekran_yazisi_cakismalari():
    baslik = "The Empty Clock Struck Twelve Every Midnight #Shorts"
    assert so.ekran_yazilari_cakisma(baslik, "IT HAD NO PENDULUM", ["WINTER 1984"], METIN) == []
    assert so.ekran_yazilari_cakisma(baslik, "THE EMPTY CLOCK STRUCK TWELVE EVERY MIDNIGHT", [], METIN)
    assert so.ekran_yazilari_cakisma(baslik, "THE CLOCK HAD NO GEARS", [], METIN)        # ilk cumle
    assert so.ekran_yazilari_cakisma(baslik, "NO GEARS", ["1984", "1984"], METIN)          # tekrar eden yazi


def test_flux_promptu_plan_ve_karakter_tarifi_icerir():
    t = so.sahne_promptu({"image_prompt": "A stickman narrator points at a clock", "shot": "close",
                          "focus": "the empty clock case"}, "Elena: woman, black hair, green coat")
    assert t.startswith("close-up shot") and "green coat" in t and "stickman" not in t.lower()


def _plan(**ek):
    p = {"planli": True, "kanca": "IT HAD NO PENDULUM", "band": False, "altyazi_ust": 1150, "altyazi_boyut": 80,
         "yazi_sorunlari": [], "sahneler": [{"src": f"g{i}.jpg", "camera": c, "text": ""}
                                           for i, c in enumerate(["pushIn", "static", "panLeft", "pushIn"])]}
    p.update(ek)
    return p


def test_gorsel_kontrol_dogrulanamayanlari_manuel_isaretler():
    r = {k["kontrol"]: k["durum"] for k in kk.gorsel_kontrol({"ekran_plani": _plan(), "gorsel_tarama": {}})}
    assert r["sahne tekrari"] == "GECTI" and r["altyazi guvenli alan"] == "GECTI"
    assert r["bozuk el/yuz/nesne"] == "MANUEL" and r["gorsel-ses uyumu"] == "MANUEL"
    assert r["gorsel on-tarama"] == "MANUEL"


def test_gorsel_kontrol_tekrar_ve_guvenli_alan_hatasi():
    plan = _plan(altyazi_ust=1400, altyazi_boyut=80)
    plan["sahneler"][1]["src"] = "g0.jpg"
    r = {k["kontrol"]: k["durum"] for k in kk.gorsel_kontrol({"ekran_plani": plan})}
    assert r["sahne tekrari"] == "KALDI" and r["altyazi guvenli alan"] == "KALDI"


def test_manuel_yayini_engellemez_kaldi_engeller():
    temel = {"baslik": "The Empty Clock Struck Twelve", "aciklama": "This is a fictional story, created for fun.",
             "etiketler": ["horror story"], "aile": "ozgun_korku", "medya_kaynagi": ["cloudflare-flux"],
             "ekran_plani": _plan()}
    ok = [k for k in kk.icerik_kontrol(temel) + kk.gorsel_kontrol(temel) if k["durum"] == "KALDI"]
    assert ok == []
    temel["ekran_plani"] = _plan(yazi_sorunlari=["kanca yazisi basligi tekrar ediyor"])
    assert any(k["durum"] == "KALDI" for k in kk.gorsel_kontrol(temel))


def test_stil_karsilastirmasi_az_veride_karar_vermez():
    import kanal_analiz as ka
    videolar = [{"video_id": f"v{i}", "gorsel_stil": "AB"[i % 2], "yayin": "2026-10-01T00:00:00Z"} for i in range(4)]
    vid_an = {"v0": {"averageViewPercentage": 80, "averageViewDuration": 30, "subscribersGained": 2}}
    o = ka.stil_karsilastir(videolar, {}, vid_an)
    assert o["A"]["sayi"] == 2 and o["A"]["izleme_yuzdesi_n"] == 1 and o["B"]["izleme_yuzdesi"] is None
