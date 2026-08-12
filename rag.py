# -*- coding: utf-8 -*-
"""
VHS Erftstadt RAG - Terminal Testi
--------------------------------------
Bu, rag_core.py'deki mantığı terminalde test etmemizi sağlayan basit bir arayüz.
"""

from rag_core import cevap_uret

if __name__ == "__main__":
    while True:
        soru = input("Sorunuzu yazın (çıkmak için 'q'): ").strip()
        if soru.lower() == "q":
            break
        if not soru:
            continue

        print("\nDüşünülüyor...\n")
        cevap = cevap_uret(soru)
        print("--- CEVAP ---")
        print(cevap)
        print()
