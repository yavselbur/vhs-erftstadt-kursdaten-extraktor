# -*- coding: utf-8 -*-
"""VHS JSON dosyasindaki kurs basliklarini dil anahtar kelimelerine gore sayar.
Kullanim: python3 dil_sayimi.py kurslar_tumu.json  (veya baska bir json dosyasi)
"""
import json
import sys
import re

DIL_ANAHTARLARI = {
    "Deutsch": ["deutsch"],
    "Englisch": ["englisch"],
    "Franzosisch": ["französisch", "franzoesisch"],
    "Spanisch": ["spanisch"],
    "Italienisch": ["italienisch"],
    "Niederlaendisch": ["niederländisch", "niederlaendisch"],
    "Portugiesisch": ["portugiesisch"],
    "Gebaerdensprache": ["gebärdensprache", "gebaerdensprache"],
}

def calistir(dosya_adi):
    with open(dosya_adi, encoding="utf-8") as f:
        kurslar = json.load(f)

    print(f"Toplam kayit: {len(kurslar)}")

    sayaclar = {dil: 0 for dil in DIL_ANAHTARLARI}
    diger = []

    for k in kurslar:
        baslik = (k.get("baslik") or "").lower()
        eslesti = False
        for dil, kelimeler in DIL_ANAHTARLARI.items():
            if any(kw in baslik for kw in kelimeler):
                sayaclar[dil] += 1
                eslesti = True
                break
        if not eslesti:
            diger.append(k.get("baslik", ""))

    print("\n--- Dile gore kurs sayisi ---")
    for dil, sayi in sayaclar.items():
        print(f"  {dil}: {sayi}")

    print(f"\n--- Hicbir dil anahtar kelimesine uymayan (Deutsch und Fremdsprachen disi olabilir): {len(diger)} ---")
    for b in diger[:10]:
        print(f"  - {b}")

if __name__ == "__main__":
    dosya = sys.argv[1] if len(sys.argv) > 1 else "kurslar_tumu.json"
    calistir(dosya)
