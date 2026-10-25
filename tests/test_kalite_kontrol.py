import subprocess

import pytest

import kalite_kontrol as kk


def _video(yol, boyut="1080x1920", sure=20, kaynak="testsrc2", ses="sine=frequency=440"):
    komut = [kk.ffmpeg_yolu(), "-y", "-loglevel", "error",
             "-f", "lavfi", "-i", f"{kaynak}=size={boyut}:rate=15:duration={sure}" if kaynak != "black"
             else f"color=c=black:size={boyut}:rate=15:duration={sure}",
             "-f", "lavfi", "-i", f"{ses}:duration={sure}" if ses.startswith("sine") else f"anullsrc=r=44100:cl=stereo",
             "-t", str(sure), "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
             "-c:a", "aac", "-shortest", str(yol)]
    subprocess.run(komut, check=True)
    return str(yol)


def _durum(rapor, ad):
    return next(k["durum"] for k in rapor if k["kontrol"] == ad)


@pytest.fixture(scope="module")
def iyi_video(tmp_path_factory):
    return _video(tmp_path_factory.mktemp("v") / "iyi.mp4")


def test_saglam_video_gecer(iyi_video):
    r = kk.teknik_kontrol(iyi_video)
    assert all(k["durum"] == "GECTI" for k in r), r


def test_yatay_video_kalir(tmp_path):
    r = kk.teknik_kontrol(_video(tmp_path / "yatay.mp4", boyut="1920x1080"))
    assert _durum(r, "cozunurluk") == "KALDI"


def test_siyah_video_kalir(tmp_path):
    r = kk.teknik_kontrol(_video(tmp_path / "siyah.mp4", kaynak="black"))
    assert _durum(r, "siyah/bos kare") == "KALDI"


def test_sessiz_video_kalir(tmp_path):
    r = kk.teknik_kontrol(_video(tmp_path / "sessiz.mp4", ses="anullsrc"))
    assert _durum(r, "ses seviyesi") == "KALDI"


def test_cok_kisa_video_kalir(tmp_path):
    r = kk.teknik_kontrol(_video(tmp_path / "kisa.mp4", sure=5))
    assert _durum(r, "sure") == "KALDI"


def test_olmayan_dosya_kalir():
    r = kk.teknik_kontrol("/yok/boyle/bir/dosya.mp4")
    assert r[0]["durum"] == "KALDI"


META = {"baslik": "The Door Was Locked From The Inside #Shorts",
        "aciklama": "A short eerie story about a locked room and what was found inside it. #shorts #mystery",
        "etiketler": ["mystery", "shorts"], "medya_kaynagi": ["cloudflare-flux", "edge-tts", "sentetik-ses"]}


def test_kurgu_etiketsiz_kalir():
    r = kk.icerik_kontrol({**META, "aile": "ozgun_korku"})
    assert _durum(r, "kurgu etiketi") == "KALDI"


def test_kurgu_etiketli_gecer():
    m = {**META, "aile": "hayatta_kalma", "aciklama": "This is a fictional story. " + META["aciklama"]}
    assert _durum(kk.icerik_kontrol(m), "kurgu etiketi") == "GECTI"


def test_gercek_vaka_kaynaksiz_kalir():
    r = kk.icerik_kontrol({**META, "aile": "gercek_vaka", "kaynak": {"dogrulandi": False}})
    assert _durum(r, "kaynak dogrulama") == "KALDI"


def test_bilinmeyen_medya_kalir():
    r = kk.icerik_kontrol({**META, "medya_kaynagi": ["youtube-indirme"]})
    assert _durum(r, "medya lisansi") == "KALDI"


def test_kontrol_et_birlesik(iyi_video):
    m = {**META, "aile": "hayatta_kalma", "aciklama": "This is a fictional story. " + META["aciklama"]}
    assert kk.kontrol_et(iyi_video, m)["gecti"] is True
