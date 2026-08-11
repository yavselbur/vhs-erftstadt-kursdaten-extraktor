# -*- coding: utf-8 -*-
"""
VHS Erftstadt RAG - Adım 3c: Tam RAG Akışı (Arama + Cevap Üretme)
---------------------------------------------------------------------
Bu program, önceki adımlardaki "arama" (retrieval) işlemini,
Ollama'daki yapay zeka modeliyle (qwen2.5:7b) birleştirir.

Akış:
1. Kullanıcı soru sorar (herhangi bir dilde).
2. En alakalı 5 kurs bulunur (Chroma veritabanından).
3. Bu 5 kursun bilgisi modele "bağlam" (context) olarak verilir.
4. Model, SADECE bu bilgilere dayanarak, kullanıcının dilinde cevap üretir.

Not: Ollama'nın kendi sunucusunun (arka planda) çalışıyor olması gerekir.
Kontrol etmek için terminalde: ollama list
"""

from sentence_transformers import SentenceTransformer
import chromadb
import requests

VERITABANI_KLASORU = "chroma_db"
OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL_ADI = "qwen2.5:7b"
KAC_SONUC = 5


def baglam_olustur(sonuclar):
    """Chroma'dan gelen arama sonuçlarını, modele okunabilir bir metin haline getirir."""
    parcalar = []
    for i in range(len(sonuclar["ids"][0])):
        m = sonuclar["metadatas"][0][i]
        belge = sonuclar["documents"][0][i]
        parca = (
            f"Kurs: {m['baslik']}\n"
            f"Tarih: {m['tarih']}\n"
            f"Yer: {m['yer']}\n"
            f"Ücret: {m['ucret']}\n"
            f"Kategori: {m['kategori']}\n"
            f"Açıklama: {belge}\n"
            f"Link: {m['link']}\n"
        )
        parcalar.append(parca)
    return "\n---\n".join(parcalar)


def ollamaya_sor(soru, baglam):
    """Ollama'ya (yerel modele) soruyu ve bağlamı gönderir, cevabı döndürür."""
    sistem_talimati = (
        "Sen VHS Erftstadt (Halk Eğitim Merkezi) için çalışan bir bilgi asistanısın. "
        "Sana verilen kurs bilgilerine SADECE dayanarak kullanıcının sorusunu cevapla. "
        "Kullanıcı hangi dilde soru sorduysa, cevabını da AYNI dilde ver. "
        "Verilen kurslar arasında, kullanıcının sorusuyla gerçekten alakalı OLMAYANLARI cevabına dahil etme. "
        "Eğer hiçbir kurs alakalı değilse, bunu dürüstçe belirt. "
        "Kurs bilgisi dışında bir şey uydurma."
    )

    kullanici_mesaji = (
        f"Kullanıcının sorusu: {soru}\n\n"
        f"Elimizdeki kurs bilgileri:\n{baglam}\n\n"
        f"Yukarıdaki bilgilere dayanarak kullanıcının sorusunu cevapla."
    )

    response = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL_ADI,
            "messages": [
                {"role": "system", "content": sistem_talimati},
                {"role": "user", "content": kullanici_mesaji},
            ],
            "stream": False,
        },
        timeout=120,
    )
    response.raise_for_status()
    return response.json()["message"]["content"]


if __name__ == "__main__":
    print("Model ve veritabanı yükleniyor...")
    embed_model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
    client = chromadb.PersistentClient(path=VERITABANI_KLASORU)
    koleksiyon = client.get_collection("vhs_kurslar")
    print(f"Hazır. Veritabanında {koleksiyon.count()} kurs var.\n")

    while True:
        soru = input("Sorunuzu yazın (çıkmak için 'q'): ").strip()
        if soru.lower() == "q":
            break
        if not soru:
            continue

        soru_embedding = embed_model.encode([soru]).tolist()
        sonuclar = koleksiyon.query(query_embeddings=soru_embedding, n_results=KAC_SONUC)

        baglam = baglam_olustur(sonuclar)

        print("\nDüşünülüyor...\n")
        cevap = ollamaya_sor(soru, baglam)
        print("--- CEVAP ---")
        print(cevap)
        print()
