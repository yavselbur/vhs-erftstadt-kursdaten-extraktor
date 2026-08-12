# -*- coding: utf-8 -*-
"""
VHS Erftstadt RAG - Adım 3a (v2): Kursları veritabanına yükleme
---------------------------------------------------------------------
Bu sürüm, kurs günleri/eğitmen bilgilerini de içeren "kurslar_gunlu.json"
dosyasını kullanıyor ve bu ek bilgileri de veritabanına (metadata olarak) kaydediyor.
"""

from sentence_transformers import SentenceTransformer
import chromadb
import json

GIRIS_DOSYASI = "kurslar_gunlu.json"
VERITABANI_KLASORU = "chroma_db"

print("Çok dilli embedding modeli yükleniyor...")
model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")

print("Kurslar okunuyor...")
with open(GIRIS_DOSYASI, "r", encoding="utf-8") as f:
    kurslar_ham = json.load(f)

gorulen_no = set()
kurslar = []
for k in kurslar_ham:
    if k["kurs_no"] in gorulen_no:
        continue
    gorulen_no.add(k["kurs_no"])
    kurslar.append(k)

print(f"{len(kurslar_ham)} kayıt okundu, tekilleştirme sonrası {len(kurslar)} benzersiz kurs kaldı.")

metinler = [f"{k['baslik']}. {k['aciklama']}" for k in kurslar]

print("Embedding'e çevriliyor...")
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
            "egitmenler": k.get("egitmenler", ""),
            "ilk_gun": k.get("ilk_gun", ""),
            "son_gun": k.get("son_gun", ""),
            "gun_sayisi": k.get("gun_sayisi", 0),
        }
        for k in kurslar
    ],
)

print(f"\nTAMAMLANDI. {len(kurslar)} kurs '{VERITABANI_KLASORU}' klasöründeki veritabanına kaydedildi.")
