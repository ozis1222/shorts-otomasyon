"""
Satis mesaji yardimcisi.

Isletmeye ozel mesaj TASLAKLARI uretir. Mesaj GONDERMEZ.
Otomatik WhatsApp / e-posta gonderimi bilincli olarak yapilmaz.
Kullanici mesajlari panelden kopyalar ve kendisi elle gonderir.

Mesajlar; lead sebeplerinden ve isletme bilgilerinden turetilir, uydurma
bilgi icermez.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..models import Business


@dataclass
class MessageDrafts:
    whatsapp: str
    email_subject: str
    email_body: str
    short: str
    demo_intro: str


def _demo_link(business: Business, base_url: str) -> str:
    if business.demo and business.demo.demo_slug:
        return f"{base_url}/demo/{business.demo.demo_slug}"
    return "[DEMO_LINK]"


def _reason_phrase(business: Business) -> str:
    """Lead sebeplerini kibar bir cumleye cevirir."""
    analysis = business.analysis
    if not business.website or (analysis and not analysis.website_exists):
        return "isletmenizin henuz bir web sitesi bulunmadigini"
    problems = []
    if analysis:
        if not analysis.mobile_friendly:
            problems.append("mobil kullanim")
        if not (analysis.https_enabled and analysis.ssl_ok):
            problems.append("guvenlik (HTTPS)")
        if analysis.looks_outdated:
            problems.append("tasarim guncelligi")
        if not analysis.has_booking:
            problems.append("online randevu")
    if problems:
        return "mevcut web sitenizde " + ", ".join(problems) + " tarafinda gelistirilebilecek noktalar oldugunu"
    return "dijital gorunurlugunuzu daha da guclendirebilecegimizi"


def build_drafts(business: Business, base_url: str) -> MessageDrafts:
    name = business.name
    reason = _reason_phrase(business)
    demo = _demo_link(business, base_url)

    whatsapp = (
        f"Merhaba, {name} icin dijital gorunurlugunuzu incelerken {reason} fark ettim.\n\n"
        f"Size gostermek icin isletmenize ozel ornek bir tasarim hazirladim.\n\n"
        f"Demo:\n{demo}\n\n"
        f"Incelemek isterseniz memnuniyetle detaylari paylasabilirim."
    )

    short = (
        f"Merhaba, {name} icin isletmenize ozel modern bir ornek web tasarimi hazirladim. "
        f"Kisaca gostermemi ister misiniz? Demo: {demo}"
    )

    email_subject = f"{name} icin ornek web tasarim onerisi"
    email_body = (
        f"Merhaba,\n\n"
        f"{name} isletmesinin dijital gorunurlugunu incelerken {reason} gozlemledim. "
        f"Bu dogrultuda isletmenize ozel, modern ve mobil uyumlu bir ornek tasarim hazirladim.\n\n"
        f"Ornek tasarimi su adresten inceleyebilirsiniz:\n{demo}\n\n"
        f"Uygun olursaniz kisa bir gorusmede detaylari ve nasil ilerleyebilecegimizi "
        f"paylasmaktan memnuniyet duyarim.\n\n"
        f"Iyi calismalar dilerim."
    )

    demo_intro = (
        f"{name} icin hazirladigim ornek tasarimi buradan gorebilirsiniz: {demo}\n"
        f"(Bu bir demo/ornek calismadir; icerik ve gorseller size gore ozellestirilir.)"
    )

    return MessageDrafts(
        whatsapp=whatsapp,
        email_subject=email_subject,
        email_body=email_body,
        short=short,
        demo_intro=demo_intro,
    )
