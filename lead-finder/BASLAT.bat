@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Lead Finder

echo ============================================================
echo   Lead Finder - kurulum ve baslatma
echo ============================================================
echo.

REM --- Python var mi? ---
where python >nul 2>nul
if errorlevel 1 (
  echo [HATA] Python bulunamadi.
  echo.
  echo Lutfen su adresten Python 3.10 veya ustunu kurun:
  echo    https://www.python.org/downloads/
  echo Kurulum sirasinda "Add Python to PATH" kutucugunu MUTLAKA isaretleyin.
  echo Kurduktan sonra bu dosyayi tekrar cift tiklayin.
  echo.
  pause
  exit /b 1
)

REM --- Sanal ortam yoksa olustur ---
if not exist ".venv\Scripts\python.exe" (
  echo Ilk kurulum: sanal ortam olusturuluyor...
  python -m venv .venv
  if errorlevel 1 (
    echo [HATA] Sanal ortam olusturulamadi.
    pause
    exit /b 1
  )
)

REM --- Paketleri kur/guncelle ---
echo Gerekli paketler kontrol ediliyor (ilk seferde biraz surebilir)...
".venv\Scripts\python.exe" -m pip install --quiet --upgrade pip
".venv\Scripts\python.exe" -m pip install --quiet -r requirements.txt
if errorlevel 1 (
  echo [HATA] Paketler kurulamadi. Internet baglantinizi kontrol edin.
  pause
  exit /b 1
)

echo.
echo ============================================================
echo   Panel aciliyor: http://127.0.0.1:8000
echo   (Tarayici hemen acilir; sayfa bos gelirse birkac saniye
echo    sonra F5 ile yenileyin.)
echo   Durdurmak icin bu pencerede CTRL + C yapin.
echo ============================================================
echo.

REM --- Tarayiciyi ac ve sunucuyu baslat ---
start "" http://127.0.0.1:8000
".venv\Scripts\python.exe" run.py

pause
