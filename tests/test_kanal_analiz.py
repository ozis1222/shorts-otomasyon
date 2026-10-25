import kanal_analiz as ka


def test_iso_sure():
    assert ka.iso_sure_sn("PT1M5S") == 65
    assert ka.iso_sure_sn("PT45S") == 45
    assert ka.iso_sure_sn("PT1H") == 3600
    assert ka.iso_sure_sn("") == 0


def test_yasa_gore_izlenme():
    gunluk = [(0, 100), (1, 50), (2, 25), (10, 999)]
    assert ka.yasa_gore_izlenme(gunluk, 1) == 100
    assert ka.yasa_gore_izlenme(gunluk, 3) == 175
    assert ka.yasa_gore_izlenme(gunluk, 7) == 175   # 10. gun 7 gunluk pencereye girmez


def test_sure_kovasi():
    assert ka.sure_kovasi(20) == "<30 sn"
    assert ka.sure_kovasi(50) == "45-60 sn"


ESIT = {a: 1 / 3 for a in ka.AILELER}


def test_az_veriyle_dagilim_degismez():
    yeni, neden = ka.agirlik_guncelle(ESIT, {"gercek_vaka": 5000, "hayatta_kalma": 10}, {"gercek_vaka": 1, "hayatta_kalma": 1})
    assert yeni == ESIT and "yeterli veri yok" in neden


def test_iyi_aile_artar_ama_sinirli():
    yeni, _ = ka.agirlik_guncelle(ESIT, {"gercek_vaka": 3000, "hayatta_kalma": 500, "ozgun_korku": 500},
                                  {"gercek_vaka": 6, "hayatta_kalma": 6, "ozgun_korku": 6})
    assert abs(sum(yeni.values()) - 1) < 0.01
    assert yeni["gercek_vaka"] > ESIT["gercek_vaka"]
    assert yeni["gercek_vaka"] - ESIT["gercek_vaka"] <= ka.MAX_HAFTALIK_DEGISIM + 0.01
    assert all(ka.SINIR[0] - 0.01 <= v <= ka.SINIR[1] + 0.01 for v in yeni.values())


def test_tek_viral_video_stratejiyi_devirmez():
    # Ayni sayida ornek; bir ailenin medyani asiri yuksek olsa bile payi ust sinirda kalir
    yeni, _ = ka.agirlik_guncelle(ESIT, {"gercek_vaka": 10**6, "hayatta_kalma": 100, "ozgun_korku": 100},
                                  {"gercek_vaka": 3, "hayatta_kalma": 3, "ozgun_korku": 3})
    assert yeni["gercek_vaka"] <= ka.SINIR[1] + 0.01
    assert min(yeni.values()) >= ka.SINIR[0] - 0.01
