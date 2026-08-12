# -*- coding: utf-8 -*-
"""
VHS Erftstadt Scraper - Adım 4: Kurs Günleri (Termine) ve Eğitmenler
-------------------------------------------------------------------------
Bu program, her kursun detay sayfasına gidip:
- Kursun HER GÜNÜNÜ (tarih, saat, yer) tek tek çeker,
- Tüm eğitmenleri (birden fazla olabilir) doğru şekilde alır,
- Kursun ilk günü, son günü ve toplam gün sayısını hesaplar.

Bazı kurslarda tüm günler tek sayfaya sığmıyor, "Weitere Termine"
(Diğer Tarihler) linkiyle devam sayfalarına gidiyoruz.

Not: Site açıkça "bu gün tatildir" diye bir bilgi vermiyor - sadece
kursun GERÇEKTEN yapılacağı günleri listeliyor. Biz de bu günlerden
ilk/son gün ve toplam gün sayısını çıkarıyoruz.
"""

import requests
from bs4 import BeautifulSoup
import json
import re
import time
import os

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
}

BEKLEME_SURESI = 1.0
GIRIS_DOSYASI = "kurslar_detayli.json"
CIKIS_DOSYASI = "kurslar_gunlu.json"
KAYIT_ARALIGI = 20

GUN_DESENI = re.compile(
    r"Datum\s*(\d{2}\.\d{2}\.\d{4})\s*"
    r"Uhrzeit\s*([\d:]{3,5}\s*-\s*[\d:]{3,5}\s*Uhr)\s*"
    r"Ort\s*(.*?)"
    r"(?=Datum\s*\d{2}\.\d{2}\.\d{4}|Weitere Termine|Download der Kurstermine|Seite\s*\d+\s*von\s*\d+|$)",
    re.DOTALL,
)


def sayfayi_indir(url):
    response = requests.get(url, headers=HEADERS, timeout=15)
    response.raise_for_status()
    time.sleep(BEKLEME_SURESI)
    return response.text


def egitmenleri_al(soup):
    """'Kursleitung' satırındaki TÜM eğitmen isimlerini virgülle ayırarak döndürür."""
    for satir in soup.find_all("tr"):
        hucreler = satir.find_all(["th", "td"])
        if len(hucreler) < 2:
            continue
        etiket = hucreler[0].get_text(strip=True)
        if "leitung" in etiket.lower():
            isimler = [a.get_text(strip=True) for a in hucreler[1].find_all("a")]
            if isimler:
                return ", ".join(isimler)
            return hucreler[1].get_text(strip=True)
    return ""


def gunleri_ayikla(html_kodu):
    """Bir sayfanın metninden 'Datum/Uhrzeit/Ort' bloklarını bulur."""
    soup = BeautifulSoup(html_kodu, "html.parser")
    metin = soup.get_text(separator=" ", strip=True)

    gunler = []
    for eslesme in GUN_DESENI.finditer(metin):
        tarih, saat, yer = eslesme.groups()
        gunler.append({
            "tarih": tarih.strip(),
            "saat": " ".join(saat.split()),
            "yer": " ".join(yer.split()),
        })
    return gunler, soup


def sonraki_sayfa_var_mi(soup):
    """'Weitere Termine' (Diğer Tarihler) linki varsa adresini döndürür."""
    for link in soup.find_all("a", href=True):
        if "Weitere Termine" in link.get_text(strip=True):
            return link["href"]
    return None


def kurs_gunlerini_getir(url):
    """Bir kursun TÜM günlerini (gerekirse birden fazla sayfa gezerek) toplar."""
    tum_gunler = []
    egitmenler = ""
    gezilen = set()
    su_anki_url = url

    for _ in range(10):
        if su_anki_url in gezilen:
            break
        gezilen.add(su_anki_url)

        try:
            html = sayfayi_indir(su_anki_url)
        except Exception as e:
            print(f"    HATA (indirme): {e}")
            break

        gunler, soup = gunleri_ayikla(html)
        tum_gunler.extend(gunler)

        if not egitmenler:
            egitmenler = egitmenleri_al(soup)

        sonraki = sonraki_sayfa_var_mi(soup)
        if not sonraki:
            break
        su_anki_url = sonraki if sonraki.startswith("http") else "https://www.vhs-erftstadt.de" + sonraki

    benzersiz = []
    gorulen = set()
    for g in tum_gunler:
        anahtar = (g["tarih"], g["saat"])
        if anahtar not in gorulen:
            gorulen.add(anahtar)
            benzersiz.append(g)

    return benzersiz, egitmenler


def ilerlemeyi_yukle():
    if os.path.exists(CIKIS_DOSYASI):
        with open(CIKIS_DOSYASI, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def kaydet(kurslar):
    with open(CIKIS_DOSYASI, "w", encoding="utf-8") as f:
        json.dump(kurslar, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    with open(GIRIS_DOSYASI, "r", encoding="utf-8") as f:
        tum_kurslar = json.load(f)

    islenmis = ilerlemeyi_yukle()
    islenmis_no = {k["kurs_no"] for k in islenmis}

    print(f"Toplam {len(tum_kurslar)} kurs var, {len(islenmis)} tanesi zaten işlenmiş.")

    for i, kurs in enumerate(tum_kurslar, start=1):
        if kurs["kurs_no"] in islenmis_no:
            continue

        print(f"[{i}/{len(tum_kurslar)}] {kurs['baslik'][:50]}...")

        gunler, egitmenler = kurs_gunlerini_getir(kurs["link"])

        kurs["kurs_gunleri"] = gunler
        kurs["egitmenler"] = egitmenler or kurs.get("egitmen", "")
        kurs["gun_sayisi"] = len(gunler)
        kurs["ilk_gun"] = gunler[0]["tarih"] if gunler else ""
        kurs["son_gun"] = gunler[-1]["tarih"] if gunler else ""

        islenmis.append(kurs)

        if i % KAYIT_ARALIGI == 0:
            kaydet(islenmis)
            print(f"  -> Ara kayıt yapıldı ({len(islenmis)} kurs).")

    kaydet(islenmis)
    print(f"\nTAMAMLANDI. {len(islenmis)} kurs '{CIKIS_DOSYASI}' dosyasına kaydedildi.")
