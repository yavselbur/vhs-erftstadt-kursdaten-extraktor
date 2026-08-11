# -*- coding: utf-8 -*-
"""
VHS Erftstadt RAG - Adım 3b: Arama Testi
--------------------------------------------
Bu program, veritabanına kaydettiğimiz kurslar arasında arama yapmamızı
sağlar. Bir soru/istek yazıyorsun (hangi dilde olursa olsun), sistem
en alakalı kursları buluyor.

Bu, henüz "yapay zeka cevabı" üretmiyor - sadece "bulma" (retrieval)
kısmını test ediyoruz. Cevap üretme kısmını bir sonraki adımda ekleyeceğiz.
"""

from sentence_transformers import SentenceTransformer
import chromadb

VERITABANI_KLASORU = "chroma_db"

print("Model ve veritabanı yükleniyor...")
model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
client = chromadb.PersistentClient(path=VERITABANI_KLASORU)
koleksiyon = client.get_collection("vhs_kurslar")

print(f"Veritabanında {koleksiyon.count()} kurs var.\n")

while True:
    soru = input("Sorunuzu yazın (çıkmak için 'q'): ").strip()
    if soru.lower() == "q":
        break
    if not soru:
        continue

    soru_embedding = model.encode([soru]).tolist()

    sonuclar = koleksiyon.query(
        query_embeddings=soru_embedding,
        n_results=5,
    )

    print(f"\n--- '{soru}' için en alakalı 5 kurs ---")
    for i in range(len(sonuclar["ids"][0])):
        metadata = sonuclar["metadatas"][0][i]
        mesafe = sonuclar["distances"][0][i]
        print(f"\n{i+1}. {metadata['baslik']}")
        print(f"   Tarih: {metadata['tarih']}")
        print(f"   Kategori: {metadata['kategori']}")
        print(f"   Ücret: {metadata['ucret']}")
        print(f"   Alaka skoru (küçük=iyi): {mesafe:.3f}")
    print()
