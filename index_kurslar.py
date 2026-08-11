# -*- coding: utf-8 -*-
"""
VHS Erftstadt RAG - Adım 3a: Kursları veritabanına yükleme (indexing)
------------------------------------------------------------------------
Bu program:
1. kurslar_temiz.json dosyasındaki 408 kursu okur.
2. Her kursun başlığını + açıklamasını "embedding" (parmak izi) haline getirir.
3. Bu parmak izlerini, kurs bilgileriyle birlikte Chroma adlı veritabanına kaydeder.

Bu işlem BİR KEZ çalıştırılır. Sonra "search_kurslar.py" ile arama yapacağız.
"""

from sentence_transformers import SentenceTransformer
import chromadb
import json

GIRIS_DOSYASI = "kurslar_temiz.json"
VERITABANI_KLASORU = "chroma_db"

print("Çok dilli embedding modeli yükleniyor (ilk seferde indirme yapabilir)...")
model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")

print("Kurslar okunuyor...")
with open(GIRIS_DOSYASI, "r", encoding="utf-8") as f:
    kurslar_ham = json.load(f)

# Bazı kurslar birden fazla kategoride listelendiği için aynı kurs_no
# ile iki kez gelmiş olabilir. Burada her kurs_no'yu sadece bir kez tutuyoruz.
gorulen_no = set()
kurslar = []
for k in kurslar_ham:
    if k["kurs_no"] in gorulen_no:
        continue
    gorulen_no.add(k["kurs_no"])
    kurslar.append(k)

print(f"{len(kurslar_ham)} kayıt okundu, tekilleştirme sonrası {len(kurslar)} benzersiz kurs kaldı.")

metinler = [f"{k['baslik']}. {k['aciklama']}" for k in kurslar]

embeddingler = model.encode(metinler, show_progress_bar=True)

print("Veritabanı hazırlanıyor...")
client = chromadb.PersistentClient(path=VERITABANI_KLASORU)

try:
    client.delete_collection("vhs_kurslar")
except Exception:
    pass

koleksiyon = client.create_collection("vhs_kurslar")

koleksiyon.add(
    ids=[k["kurs_no"] for k in kurslar],
    documents=metinler,
    embeddings=embeddingler.tolist(),
    metadatas=[
        {
            "baslik": k["baslik"],
            "tarih": k["tarih"],
            "yer": k["yer"],
            "kategori": k["kategori"],
            "ucret": k["ucret"],
            "link": k["link"],
        }
        for k in kurslar
    ],
)

print(f"\nTAMAMLANDI. {len(kurslar)} kurs '{VERITABANI_KLASORU}' klasöründeki veritabanına kaydedildi.")
