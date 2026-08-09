# -*- coding: utf-8 -*-
"""
VHS Erftstadt Kurs Scraper - Adım 1
-------------------------------------
Bu program, VHS Erftstadt sitesindeki BIR kategori sayfasından
kurs bilgilerini (başlık, tarih, yer, kurs no, link) okur ve
bir JSON dosyasına kaydeder.

Nasıl çalışır (kısaca):
1. "requests" ile sayfanın HTML kodunu indiririz.
2. "BeautifulSoup" ile bu HTML kodunun içinden kurs bilgilerini ayıklarız.
3. Bulduğumuz bilgileri bir liste halinde toplayıp JSON dosyasına yazarız.
"""

import requests
from bs4 import BeautifulSoup
import json
import re
import time

# Hangi sayfayı çekeceğiz? (Şimdilik sadece "Deutsch und Fremdsprachen" kategorisi)
URL = "https://www.vhs-erftstadt.de/programm/sprachen/kategorie/Deutsch+und+Fremdsprachen/244"

# Bazı siteler, tarayıcı olmayan (bot) isteklerini reddedebiliyor.
# Bu yüzden isteğimizin normal bir tarayıcıdan geldiğini belirtiyoruz.
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
}


def sayfayi_indir(url):
    """Verilen adresteki sayfanın HTML kodunu indirir."""
    print(f"İndiriliyor: {url}")
    response = requests.get(url, headers=HEADERS, timeout=15)
    response.raise_for_status()  # Hata varsa (örn. sayfa bulunamadı) burada durur
    return response.text


def kurslari_ayikla(html_kodu):
    """
    HTML kodunun içinden kurs bilgilerini bulur.

    Sitedeki her kurs, içinde "Wann:", "Wo:", "Nr.:" kelimeleri geçen
    ve href'inde (link adresinde) "/kurs/" yazan bir <a> etiketi (link) olarak duruyor.
    Biz de bu deseni arıyoruz.
    """
    soup = BeautifulSoup(html_kodu, "html.parser")
    kurslar = []

    # href'inde "/kurs/" geçen tüm linkleri bul
    linkler = soup.find_all("a", href=re.compile(r"/kurs/"))

    for link in linkler:
        metin = link.get_text(separator=" ", strip=True)

        # "Wann:" kelimesi yoksa bu bir kurs kartı değildir, atla
        if "Wann:" not in metin:
            continue

        # Metnin içinden başlık / tarih / yer / no bilgilerini ayır
        baslik = metin.split("Wann:")[0].strip()

        tarih_eslesme = re.search(r"Wann:(.*?)Wo:", metin)
        tarih = tarih_eslesme.group(1).strip() if tarih_eslesme else ""

        yer_eslesme = re.search(r"Wo:(.*?)Nr\.:", metin)
        yer = yer_eslesme.group(1).strip() if yer_eslesme else ""

        no_eslesme = re.search(r"Nr\.:(.*)", metin)
        kurs_no = no_eslesme.group(1).strip() if no_eslesme else ""

        # Linkin tam adresini oluştur (href göreceli bir yol olabilir)
        href = link.get("href", "")
        if href.startswith("http"):
            tam_link = href
        else:
            tam_link = "https://www.vhs-erftstadt.de" + href

        kurs = {
            "baslik": baslik,
            "tarih": tarih,
            "yer": yer,
            "kurs_no": kurs_no,
            "link": tam_link,
        }
        kurslar.append(kurs)

    return kurslar


def kaydet(kurslar, dosya_adi="kurslar.json"):
    """Bulunan kursları bir JSON dosyasına yazar."""
    with open(dosya_adi, "w", encoding="utf-8") as f:
        json.dump(kurslar, f, ensure_ascii=False, indent=2)
    print(f"{len(kurslar)} kurs '{dosya_adi}' dosyasına kaydedildi.")


if __name__ == "__main__":
    html = sayfayi_indir(URL)
    kurslar = kurslari_ayikla(html)

    # Bulduklarımızı ekrana da yazdıralım, göz ile kontrol edelim
    for k in kurslar:
        print("-" * 40)
        print("Başlık :", k["baslik"])
        print("Tarih  :", k["tarih"])
        print("Yer    :", k["yer"])
        print("No     :", k["kurs_no"])
        print("Link   :", k["link"])

    kaydet(kurslar)

