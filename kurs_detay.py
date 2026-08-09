# -*- coding: utf-8 -*-
"""
VHS Erftstadt Kurs Scraper - Adım 2: Detay Sayfaları
-------------------------------------------------------
Bu program, kurslar_tumu.json dosyasındaki her kursun kendi
detay sayfasına gidip şu bilgileri ekler:
- aciklama   (kursun tanıtım metni)
- ucret      (kurs ücreti)
- sure       (kaç hafta / kaç oturum)
- egitmen    (kursu veren kişi)
- grup_buyuklugu

Not: 408 kurs olduğu için bu işlem birkaç dakika sürecek.
Eğer program yarıda kesilirse (hata, internet kopması vb.),
"kurslar_detayli.json" dosyasını tekrar çalıştırdığında kaldığı
yerden devam eder (zaten işlenmiş kursları atlar).
"""

import requests
from bs4 import BeautifulSoup
import json
import time
import os

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
}

BEKLEME_SURESI = 1.0
GIRIS_DOSYASI = "kurslar_tumu.json"
CIKIS_DOSYASI = "kurslar_detayli.json"
KAYIT_ARALIGI = 20  # Her 20 kursta bir dosyaya kaydet (güvenlik için)


def detay_cek(url):
    """Bir kursun detay sayfasına gidip açıklama, ücret, süre gibi bilgileri toplar."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
    except Exception as e:
        print(f"    HATA (indirme): {e}")
        return {}

    soup = BeautifulSoup(response.text, "html.parser")

    detay = {
        "aciklama": "",
        "ucret": "",
        "sure": "",
        "egitmen": "",
        "grup_buyuklugu": "",
    }

    meta_aciklama = soup.find("meta", attrs={"name": "description"})
    if meta_aciklama and meta_aciklama.get("content"):
        detay["aciklama"] = meta_aciklama["content"].strip()

    for satir in soup.find_all("tr"):
        hucreler = satir.find_all(["th", "td"])
        if len(hucreler) < 2:
            continue
        etiket = hucreler[0].get_text(strip=True)
        deger = hucreler[1].get_text(strip=True)

        if "gebühr" in etiket.lower():
            detay["ucret"] = deger
        elif "dauer" in etiket.lower():
            detay["sure"] = deger
        elif "leitung" in etiket.lower():
            detay["egitmen"] = deger
        elif "größe" in etiket.lower():
            detay["grup_buyuklugu"] = deger

    return detay


def ilerlemeyi_yukle():
    """Daha önce kaydedilmiş bir 'kurslar_detayli.json' varsa onu yükler."""
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

    islenmis_kurslar = ilerlemeyi_yukle()
    islenmis_no_seti = {k["kurs_no"] for k in islenmis_kurslar}

    print(f"Toplam {len(tum_kurslar)} kurs var, {len(islenmis_kurslar)} tanesi zaten işlenmiş.")

    for i, kurs in enumerate(tum_kurslar, start=1):
        if kurs["kurs_no"] in islenmis_no_seti:
            continue

        print(f"[{i}/{len(tum_kurslar)}] {kurs['baslik'][:50]}...")

        detay = detay_cek(kurs["link"])
        kurs.update(detay)
        islenmis_kurslar.append(kurs)

        time.sleep(BEKLEME_SURESI)

        if i % KAYIT_ARALIGI == 0:
            kaydet(islenmis_kurslar)
            print(f"  -> Ara kayıt yapıldı ({len(islenmis_kurslar)} kurs).")

    kaydet(islenmis_kurslar)
    print(f"\nTAMAMLANDI. {len(islenmis_kurslar)} kurs '{CIKIS_DOSYASI}' dosyasına kaydedildi.")
