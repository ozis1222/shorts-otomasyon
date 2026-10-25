import json

import pytest

import shorts_otomasyon as so
import yayinla


def test_aile_ust_uste_ucuncu_kez_secilmez(monkeypatch):
    monkeypatch.delenv("ICERIK_AILESI", raising=False)
    gecmis = [{"aile": "ozgun_korku"}, {"aile": "ozgun_korku"}]
    for _ in range(50):
        assert so.aile_sec(gecmis) != "ozgun_korku"


def test_kurgu_aciklamasina_etiket_eklenir():
    a = so.aciklama_son_hali("A story.", "hayatta_kalma", {}, "cloudflare-flux")
    assert so.KURGU_NOTU in a and "AI image tools" in a


def test_gercek_vaka_aciklamasina_kaynak_eklenir():
    a = so.aciklama_son_hali("A case.", "gercek_vaka", {"url": "https://en.wikipedia.org/wiki/X"}, "kod-cizim")
    assert "Source: https://en.wikipedia.org/wiki/X" in a and so.KURGU_NOTU not in a


def test_her_aile_icin_prompt_kurulur():
    for aile in so.AILELER:
        p = so._prompt_kur([], None, [], [], aile)
        assert "100-140 words" in p
        assert ("FICTION RULES" in p) == (aile != "gercek_vaka")


def test_svg_temizleme_zararli_icerigi_siler():
    ham = ('<svg viewBox="0 0 10 10"><script>alert(1)</script><rect onclick="x()" width="1" height="1"/>'
           '<a href="http://kotu.site"><circle r="1"/></a><rect/><rect/><rect/><rect/></svg>')
    temiz = so._svg_temizle(ham, 600, 600)
    assert temiz and "script" not in temiz and "onclick" not in temiz and "kotu.site" not in temiz


def test_tekrar_eden_vaka_yakalanir():
    gecmis = [{"topic": "The Dyatlov Pass Incident", "title": "Nine Hikers Cut Their Tent From Inside"}]
    assert so.tekrar_mi("Dyatlov Pass 1959", "Dyatlov Hikers", "", gecmis)


def _paket(tmp_path, gecti=True, paket_id="p1"):
    k = tmp_path / "paket"
    k.mkdir()
    (k / "video.mp4").write_bytes(b"0" * 100)
    (k / "meta.json").write_text(json.dumps({"paket_id": paket_id, "baslik": "The Empty Clock Struck Twelve #Shorts",
                                             "aciklama": "This is a fictional story, created for entertainment only.",
                                             "aile": "ozgun_korku", "etiketler": ["horror story", "true mystery"],
                                             "medya_kaynagi": ["cloudflare-flux"],
                                             "kalite": {"gecti": gecti, "kontroller": []}}))
    return str(k)


def test_yayinla_kaliteden_gecmeyeni_yuklemez(tmp_path):
    with pytest.raises(SystemExit, match="kalite"):
        yayinla.main(["--paket", _paket(tmp_path, gecti=False), "--deneme"])


def test_yayinla_cift_yayini_engeller(tmp_path, monkeypatch):
    kayit = tmp_path / "videolar.json"
    kayit.write_text(json.dumps({"videolar": [{"paket_id": "p1", "video_id": "abc"}]}))
    monkeypatch.setattr(so, "VIDEOLAR_FILE", str(kayit))
    with pytest.raises(SystemExit, match="zaten yuklenmis"):
        yayinla.main(["--paket", _paket(tmp_path), "--deneme"])


def test_yayinla_deneme_modu_yuklemez(tmp_path, monkeypatch):
    monkeypatch.setattr(so, "VIDEOLAR_FILE", str(tmp_path / "yok.json"))
    monkeypatch.setattr(so, "youtube_yukle", lambda *a, **k: pytest.fail("deneme modunda yukleme yapildi"))
    assert yayinla.main(["--paket", _paket(tmp_path), "--deneme"]) == 0


def test_kurgu_seo_gercek_olay_etiketi_eklemez():
    import shorts_otomasyon as so
    _, ac, et = so._seo_duzenle("Baslik burada", "Kisa aciklama metni burada",
                                ["true story", "creepy tale", "cold case shorts"], "The Blackwood Clock", "ozgun_korku")
    assert not any(g in e.lower() for e in et for g in ("true", "cold case", "unsolved"))
    assert "#truestory" not in ac.lower()
    _, _, et2 = so._seo_duzenle("Baslik burada", "Kisa aciklama", [], "Dyatlov Pass", "gercek_vaka")
    assert "true mystery" in et2


def test_yaygin_kelime_ayni_vaka_sayilmaz():
    import shorts_otomasyon as so
    gecmis = [{"topic": "The Disappearance of Lars Mittank",
               "title": "Security Cameras Caught Lars Mittank Running into the Woods #Shorts"}]
    assert so.tekrar_mi("The Oakhaven Vault Footage Anomaly", "Security Footage Shows Empty Vault Opening",
                        "", gecmis) is None
    assert so.tekrar_mi("Mittank sighting", "Was Lars Mittank Seen Again?", "", gecmis)


def test_anlatici_flux_promptundan_cikar():
    import shorts_otomasyon as so
    t = so._ANLATICI_RE.sub("a frightened witness", "A stickman narrator pointing at a clock")
    assert "stickman" not in t.lower() and "narrator" not in t.lower()
