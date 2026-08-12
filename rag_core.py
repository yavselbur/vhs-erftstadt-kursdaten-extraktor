# -*- coding: utf-8 -*-
"""
VHS Erftstadt RAG - Ortak Çekirdek Modül (v2)
----------------------------------------------------
Yeni eklenenler:
1. Zaman durumu hesaplama: her kursun "henüz başlamadı / devam ediyor / bitti"
   durumunu, BİLGİSAYARIN GERÇEK TARİHİNE göre Python ile kesin hesaplıyoruz.
2. Kategori bazlı tam liste: "X kategorisindeki TÜM kursları listele" gibi
   isteklerde, embedding aramasını atlayıp veritabanından o kategorideki
   HER ŞEYİ çekiyoruz - hızlı ve %100 güvenilir.
"""

from sentence_transformers import SentenceTransformer
import chromadb
import requests
from datetime import datetime, date

VERITABANI_KLASORU = "chroma_db"
OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL_ADI = "qwen2.5:7b"
KAC_SONUC = 5

print("RAG çekirdeği yükleniyor (model + veritabanı)...")
_embed_model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
_client = chromadb.PersistentClient(path=VERITABANI_KLASORU)
_koleksiyon = _client.get_collection("vhs_kurslar")
print(f"Hazır. Veritabanında {_koleksiyon.count()} kurs var.")


def _tarihi_coz(tarih_metni):
    """'03.09.2026' gibi bir metni Python tarih nesnesine çevirir. Olmazsa None döner."""
    try:
        return datetime.strptime(tarih_metni.strip(), "%d.%m.%Y").date()
    except (ValueError, AttributeError):
        return None


def _durumu_hesapla(ilk_gun, son_gun):
    """Bir kursun ilk/son gününe bakıp bugüne göre durumunu hesaplar."""
    bugun = date.today()
    ilk = _tarihi_coz(ilk_gun)
    son = _tarihi_coz(son_gun)

    if not ilk or not son:
        return "Tarih bilgisi eksik/belirsiz"

    if bugun < ilk:
        kalan = (ilk - bugun).days
        return f"Henüz başlamadı ({kalan} gün sonra başlıyor, {ilk_gun})"
    elif ilk <= bugun <= son:
        return f"Şu anda devam ediyor ({ilk_gun} - {son_gun} arası)"
    else:
        gecen = (bugun - son).days
        return f"Tamamlandı ({gecen} gün önce bitti, son gün: {son_gun})"


_KATEGORI_ESLESTIRME = {
    "Deutsch und Fremdsprachen": ["deutsch", "fremdsprachen", "sprachen", "dil ", "diller", "language", "ıspanyolca", "spanisch", "englisch", "französisch"],
    "Gesundheit und Ernährung": ["gesundheit", "ernährung", "sağlık", "health", "yoga", "fitness"],
    "Kultur und Kreativität": ["kultur", "kreativ", "kültür", "culture", "sanat"],
    "Mensch und Gesellschaft": ["mensch", "gesellschaft", "toplum", "society"],
    "Berufliche Bildung": ["beruflich", "meslek", "professional", "career", "edv"],
    "Grundbildung und Schulabschlussberatung": ["grundbildung", "schulabschluss", "temel eğitim"],
    "Vorträge und Exkursionen": ["vortr", "exkursion", "gezi", "konferans", "lecture"],
}

_LISTELEME_TETIKLEYICILERI = [
    "tüm", "tümü", "hepsi", "bütün", "listele", "liste",
    "all", "list", "alle", "sämtliche", "complete list",
]


def _kategori_listesi_mi(soru):
    """Sorunun 'bir kategorideki TÜM kursları listele' anlamına gelip gelmediğini tahmin eder."""
    soru_kucuk = soru.lower()

    tetikleyici_var = any(t in soru_kucuk for t in _LISTELEME_TETIKLEYICILERI)
    if not tetikleyici_var:
        return None

    for kategori_adi, anahtar_kelimeler in _KATEGORI_ESLESTIRME.items():
        if any(ak in soru_kucuk for ak in anahtar_kelimeler):
            return kategori_adi

    return None


def _kategori_tam_listesi(kategori_adi):
    """Bir kategorideki TÜM kursları veritabanından çeker."""
    sonuc = _koleksiyon.get(where={"kategori": kategori_adi})
    metadatalar = sonuc["metadatas"]

    if not metadatalar:
        return f"'{kategori_adi}' kategorisinde kurs bulunamadı."

    satirlar = [f"'{kategori_adi}' kategorisinde {len(metadatalar)} kurs bulundu:\n"]
    for m in metadatalar:
        durum = _durumu_hesapla(m.get("ilk_gun", ""), m.get("son_gun", ""))
        satirlar.append(f"• {m['baslik']} — {m['tarih']} — {durum}")

    return "\n".join(satirlar)


def _baglam_olustur(sonuclar):
    """Chroma'dan gelen arama sonuçlarını, modele okunabilir bir metin haline getirir."""
    parcalar = []
    for i in range(len(sonuclar["ids"][0])):
        m = sonuclar["metadatas"][0][i]
        belge = sonuclar["documents"][0][i]
        durum = _durumu_hesapla(m.get("ilk_gun", ""), m.get("son_gun", ""))
        parca = (
            f"Kurs: {m['baslik']}\n"
            f"Tarih: {m['tarih']}\n"
            f"Yer: {m['yer']}\n"
            f"Ücret: {m['ucret']}\n"
            f"Kategori: {m['kategori']}\n"
            f"Eğitmen(ler): {m.get('egitmenler', '')}\n"
            f"Durum: {durum}\n"
            f"Açıklama: {belge}\n"
            f"Link: {m['link']}\n"
        )
        parcalar.append(parca)
    return "\n---\n".join(parcalar)


def _ollamaya_sor(soru, baglam):
    """Ollama'ya (yerel modele) soruyu ve bağlamı gönderir, cevabı döndürür."""
    bugun_str = date.today().strftime("%d.%m.%Y")

    sistem_talimati = (
        "Sen VHS Erftstadt (Halk Eğitim Merkezi) için çalışan bir bilgi asistanısın. "
        f"Bugünün tarihi {bugun_str}. "
        "Sana verilen kurs bilgilerine SADECE dayanarak kullanıcının sorusunu cevapla. "
        "Her kursun yanında verilen 'Durum' bilgisini OLDUĞU GİBİ kullan, kendin tarih hesaplaması YAPMA. "
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
    İki yoldan biriyle çalışır:
    1. Soru "kategorideki tüm kursları listele" anlamına geliyorsa -> doğrudan liste
    2. Değilse -> normal embedding araması + yapay zeka cevabı
    """
    kategori = _kategori_listesi_mi(soru)
    if kategori:
        return _kategori_tam_listesi(kategori)

    soru_embedding = _embed_model.encode([soru]).tolist()
    sonuclar = _koleksiyon.query(query_embeddings=soru_embedding, n_results=KAC_SONUC)
    baglam = _baglam_olustur(sonuclar)
    return _ollamaya_sor(soru, baglam)
