# -*- coding: utf-8 -*-
"""
VHS Erftstadt RAG - Ortak Çekirdek Modül
--------------------------------------------
Bu dosya, "soru sor -> alakalı kursları bul -> cevap üret" mantığını
tek bir yerde toplar. Hem terminal testinde (rag.py) hem de
Telegram botunda (bot.py) buradaki fonksiyonlar kullanılır.
"""

from sentence_transformers import SentenceTransformer
import chromadb
import requests

VERITABANI_KLASORU = "chroma_db"
OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL_ADI = "qwen2.5:7b"
KAC_SONUC = 5

print("RAG çekirdeği yükleniyor (model + veritabanı)...")
_embed_model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
_client = chromadb.PersistentClient(path=VERITABANI_KLASORU)
_koleksiyon = _client.get_collection("vhs_kurslar")
print(f"Hazır. Veritabanında {_koleksiyon.count()} kurs var.")


def _baglam_olustur(sonuclar):
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


def _ollamaya_sor(soru, baglam):
    """Ollama'ya (yerel modele) soruyu ve bağlamı gönderir, cevabı döndürür."""
    sistem_talimati = (
        "Sen VHS Erftstadt (Halk Eğitim Merkezi) için çalışan bir bilgi asistanısın. "
        "Sana verilen kurs bilgilerine SADECE dayanarak kullanıcının sorusunu cevapla. "
        "Kullanıcı hangi dilde soru sorduysa, cevabını da AYNI dilde ver. "
        "Verilen kurslar arasında, kullanıcının sorusuyla gerçekten alakalı OLMAYANLARI cevabına dahil etme. "
        "Eğer hiçbir kurs alakalı değilse, bunu dürüstçe belirt. "
        "Kurs bilgisi dışında bir şey uydurma. Cevabını kısa ve net tut, Telegram'da okunacak."
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


def cevap_uret(soru):
    """
    Dışarıdan çağrılacak ana fonksiyon: bir soru metni alır,
    tam RAG akışını çalıştırır, cevap metnini döndürür.
    """
    soru_embedding = _embed_model.encode([soru]).tolist()
    sonuclar = _koleksiyon.query(query_embeddings=soru_embedding, n_results=KAC_SONUC)
    baglam = _baglam_olustur(sonuclar)
    return _ollamaya_sor(soru, baglam)
