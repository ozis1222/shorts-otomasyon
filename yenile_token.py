# -*- coding: utf-8 -*-
"""
token.json YENILEME ARACI  (sadece KENDI bilgisayarinda calistir)

Ne ise yarar?
  Eski token.json yalnizca "video yukleme" yetkisine sahipti. Otomasyonun
  KENDI KANALININ ISTATISTIKLERINDEN OGRENMESI icin "okuma" yetkisi de gerekiyor.
  Bu arac tarayicini acar, Google hesabinla izin verirsin ve yeni token.json uretir.

Nasil calistirilir?
  1) client_secret.json bu klasorde olsun.
  2) python yenile_token.py
  3) Acilan tarayicida YouTube kanalinin sahibi olan hesabi sec ve izin ver.
  4) Olusan token.json'un ICERIGINI GitHub'da
     Settings > Secrets and variables > Actions > TOKEN_JSON secret'ina yapistir.

GUVENLIK: token.json bir sifre kadar gizlidir. .gitignore'da olmasi gerekir,
repoya ASLA commit etme. Bu arac icerigi ekrana YAZDIRMAZ.
"""

import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CLIENT_SECRET_FILE = os.path.join(BASE_DIR, "client_secret.json")
TOKEN_FILE = os.path.join(BASE_DIR, "token.json")

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",     # video yukleme
    "https://www.googleapis.com/auth/youtube.readonly",   # kendi istatistiklerini okuma
]


def main():
    if not os.path.exists(CLIENT_SECRET_FILE):
        print("HATA: client_secret.json bulunamadi.")
        print("Google Cloud Console > APIs & Services > Credentials > OAuth istemcisi (Desktop app)")
        print("indirip bu klasore 'client_secret.json' adiyla koy.")
        sys.exit(1)

    from google_auth_oauthlib.flow import InstalledAppFlow

    if os.path.exists(TOKEN_FILE):
        yedek = TOKEN_FILE + ".eski"
        try:
            os.replace(TOKEN_FILE, yedek)
            print(f"Mevcut token.json -> {os.path.basename(yedek)} olarak yedeklendi.")
        except OSError as e:
            print("Uyari: eski token yedeklenemedi:", e)

    print("Tarayici aciliyor... Kanalin sahibi olan Google hesabini sec ve izin ver.")
    flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
    creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")

    with open(TOKEN_FILE, "w", encoding="utf-8") as f:
        f.write(creds.to_json())

    verilen = set(creds.scopes or [])
    print("\nBASARILI. Yeni token.json olusturuldu.")
    print("Verilen yetkiler:")
    for s in sorted(verilen):
        print("  -", s)
    if not any("readonly" in s for s in verilen):
        print("\nUYARI: 'youtube.readonly' yetkisi verilmemis gorunuyor.")
        print("Izin ekraninda TUM kutulari isaretledigin den emin olup tekrar calistir.")

    print("\nSIRADAKI ADIM:")
    print("  token.json dosyasini bir metin editoruyle ac, ICERIGINI komple kopyala ve")
    print("  GitHub > repo > Settings > Secrets and variables > Actions > TOKEN_JSON")
    print("  secret'ini bu icerikle guncelle.")
    print("\nNOT: token.json'u repoya commit ETME (.gitignore zaten engelliyor).")


if __name__ == "__main__":
    main()
