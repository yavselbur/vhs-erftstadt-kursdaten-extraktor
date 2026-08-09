# -*- coding: utf-8 -*-
"""
VHS Erftstadt Kurs Scraper - Tam Sürüm
-----------------------------------------
Bu program:
1. Sitenin "Gesamtübersicht" (Genel Bakış) sayfasından tüm ana kategorileri
   kendisi bulur (elle link yazmıyoruz).
2. Her kategorinin TÜM sayfalarını gezer (1, 2, 3, ... son sayfaya kadar).
3. Bulduğu her kursu (başlık, tarih, yer, no, link, kategori) bir listede toplar.
4. Hepsini "kurslar_tumu.json" dosyasına kaydeder.
"""

import requests
from bs4 import BeautifulSoup
import json
import re
import time

BASE_URL = "https://www.vhs-erftstadt.de"
GENEL_BAKIS_URL = f"{BASE_URL}/programm/gesamtuebersicht"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
}

BEKLEME_SURESI = 1.0


def sayfayi_indir(url):
    """Verilen adresteki sayfanın HTML kodunu indirir."""
    response = requests.get(url, headers=HEADERS, timeout=15)
    response.raise_for_status()
    time.sleep(BEKLEME_SURESI)
    return response.text


def kategorileri_bul():
    """Gesamtübersicht sayfasından tüm ana kategori linklerini otomatik bulur."""
    print(f"Kategoriler bulunuyor: {GENEL_BAKIS_URL}")
    html = sayfayi_indir(GENEL_BAKIS_URL)
    soup = BeautifulSoup(html, "html.parser")

    kategoriler = {}

    for link in soup.find_all("a", href=re.compile(r"/kategorie/")):
        href = link.get("href", "")
        isim = link.get_text(strip=True)

        if not isim or "zum Kursprogramm" in isim:
            continue

        tam_link = href if href.startswith("http") else BASE_URL + href
        kategoriler[isim] = tam_link

    print(f"{len(kategoriler)} kategori bulundu: {list(kategoriler.keys())}")
    return kategoriler


def sayfa_linklerini_bul(soup):
    """Bir kategori sayfasındaki sayfalama (1, 2, 3...) linklerini bulur."""
    linkler = set()
    for link in soup.find_all("a", href=True):
        metin = link.get_text(strip=True)
        if metin.isdigit():
            href = link["href"]
            tam_link = href if href.startswith("http") else BASE_URL + href
            linkler.add(tam_link)
    return linkler


def kurslari_ayikla(soup, kategori_adi):
    """Bir sayfanın HTML'inden kurs bilgilerini çıkarır."""
    kurslar = []
    linkler = soup.find_all("a", href=re.compile(r"/kurs/"))

    for link in linkler:
        metin = link.get_text(separator=" ", strip=True)
        if "Wann:" not in metin:
            continue

        baslik = metin.split("Wann:")[0].strip()

        tarih_eslesme = re.search(r"Wann:(.*?)Wo:", metin)
        tarih = tarih_eslesme.group(1).strip() if tarih_eslesme else ""

        yer_eslesme = re.search(r"Wo:(.*?)Nr\.:", metin)
        yer = yer_eslesme.group(1).strip() if yer_eslesme else ""

        no_eslesme = re.search(r"Nr\.:(.*)", metin)
        kurs_no = no_eslesme.group(1).strip() if no_eslesme else ""

        href = link.get("href", "")
        tam_link = href if href.startswith("http") else BASE_URL + href

        kurslar.append({
            "baslik": baslik,
            "tarih": tarih,
            "yer": yer,
            "kurs_no": kurs_no,
            "link": tam_link,
            "kategori": kategori_adi,
        })

    return kurslar


def kategori_tumunu_gez(kategori_adi, ilk_url):
    """Bir kategorinin TÜM sayfalarını gezer ve kursları birleştirir."""
    print(f"\n=== Kategori: {kategori_adi} ===")

    gezilen_sayfalar = set()
    gezilecek_sayfalar = {ilk_url}
    tum_kurslar = []
    gorulen_kurs_no = set()

    while gezilecek_sayfalar:
        url = gezilecek_sayfalar.pop()
        if url in gezilen_sayfalar:
            continue
        gezilen_sayfalar.add(url)

        print(f"  Sayfa indiriliyor: {url}")
        html = sayfayi_indir(url)
        soup = BeautifulSoup(html, "html.parser")

        kurslar = kurslari_ayikla(soup, kategori_adi)
        for k in kurslar:
            if k["kurs_no"] and k["kurs_no"] not in gorulen_kurs_no:
                gorulen_kurs_no.add(k["kurs_no"])
                tum_kurslar.append(k)

        yeni_sayfalar = sayfa_linklerini_bul(soup)
        for sayfa in yeni_sayfalar:
            if sayfa not in gezilen_sayfalar:
                gezilecek_sayfalar.add(sayfa)

    print(f"  -> '{kategori_adi}' kategorisinde toplam {len(tum_kurslar)} kurs bulundu.")
    return tum_kurslar


def kaydet(kurslar, dosya_adi="kurslar_tumu.json"):
    with open(dosya_adi, "w", encoding="utf-8") as f:
        json.dump(kurslar, f, ensure_ascii=False, indent=2)
    print(f"\nTOPLAM {len(kurslar)} kurs '{dosya_adi}' dosyasına kaydedildi.")


if __name__ == "__main__":
    kategoriler = kategorileri_bul()

    tum_kurslar = []
    for kategori_adi, url in kategoriler.items():
        kurslar = kategori_tumunu_gez(kategori_adi, url)
        tum_kurslar.extend(kurslar)

    kaydet(tum_kurslar)
