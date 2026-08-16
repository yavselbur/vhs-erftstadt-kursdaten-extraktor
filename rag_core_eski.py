# -*- coding: utf-8 -*-
"""
VHS Erftstadt RAG - Ortak Çekirdek Modül (v4)
----------------------------------------------------
v4'te eklenen:
- YAPISAL FİLTRE YOLU: Soru bir kategori/dil (Deutsch, Englisch...) içeriyor VE
  seviye (A1.1) veya ay (Eylül/September) veya durum (başlayacak/beginnend) bilgisi
  taşıyorsa, embedding aramasına HİÇ girmeden önce `where` clause ile kesin
  filtreleme yapılır. Bu filtrelenmiş TAM sonuç, sonra LLM'e verilir - böylece:
    a) Farklı dillerde sorulan AYNI soru artık farklı (yanlış) embedding
       sonuçlarına düşmüyor,
    b) Cevap yine de kullanıcının sorduğu dilde LLM tarafından formatlanıyor
       (deterministik Türkçe metin döndürmüyoruz).

Bilinen sınır: kategori/ay/seviye anahtar kelime eşleştirmesi TR/DE/EN için
tanımlı. Diğer dillerde (örn. Ukraynaca) bu filtreler tetiklenmeyebilir,
sistem o durumda normal embedding aramasına geri döner.
"""

from sentence_transformers import SentenceTransformer
import chromadb
import requests
import re
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
    try:
        return datetime.strptime(tarih_metni.strip(), "%d.%m.%Y").date()
    except (ValueError, AttributeError):
        return None


def _durum_kodu(ilk_gun, son_gun):
    """Kursun durumunu KISA KOD olarak döndürür: 'baslamamis' / 'devam_eden' / 'tamamlandi' / 'belirsiz'"""
    bugun = date.today()
    ilk = _tarihi_coz(ilk_gun)
    son = _tarihi_coz(son_gun)
    if not ilk or not son:
        return "belirsiz"
    if bugun < ilk:
        return "baslamamis"
    elif ilk <= bugun <= son:
        return "devam_eden"
    else:
        return "tamamlandi"


def _durumu_hesapla(ilk_gun, son_gun):
    """İnsan tarafından okunabilir durum metni üretir."""
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
    "Deutsch und Fremdsprachen": ["deutsch", "fremdsprachen", "sprachen", "dil ", "diller", "language", "ıspanyolca", "ispanyolca", "spanisch", "spanish", "englisch", "english", "ingilizce", "französisch", "french", "fransızca", "fransizca", "almanca", "german", "hollandaca", "niederländisch", "dutch", "gebärdensprache", "işaret dili", "isaret dili", "sign language"],
    "Gesundheit und Ernährung": ["gesundheit", "ernährung", "sağlık", "health", "yoga", "fitness"],
    "Kultur und Kreativität": ["kultur", "kreativ", "kültür", "culture", "sanat"],
    "Mensch und Gesellschaft": ["mensch", "gesellschaft", "toplum", "society"],
    "Berufliche Bildung": ["beruflich", "meslek", "professional", "career", "edv"],
    "Grundbildung und Schulabschlussberatung": ["grundbildung", "schulabschluss", "temel eğitim"],
    "Vorträge und Exkursionen": ["vortr", "exkursion", "gezi", "konferans", "lecture"],
}

# --- YENİ: Spesifik dil filtresi ---
# "Deutsch und Fremdsprachen" kategorisi TEK kategoride birden çok dili barındırıyor
# (Almanca, İngilizce, İspanyolca, Fransızca, Hollandaca, İşaret Dili...).
# Sadece kategori+seviye+ay filtresi, YANLIŞ dildeki bir kursu da getirebilir.
# Bu yüzden sorgudan hangi SPESİFİK dilin kastedildiğini çıkarıp, kurs başlığında
# o dilin Almanca adının geçmesini de zorunlu kılıyoruz (başlıklar hep Almanca).
_DIL_SORGU_ANAHTARLARI = {
    "Deutsch": ["almanca", "deutsch", "german"],
    "Englisch": ["ingilizce", "englisch", "english"],
    "Spanisch": ["ispanyolca", "ıspanyolca", "spanisch", "spanish"],
    "Französisch": ["fransızca", "fransizca", "französisch", "french"],
    "Niederländisch": ["hollandaca", "niederländisch", "dutch"],
    "Gebärdensprache": ["işaret dili", "isaret dili", "gebärdensprache", "sign language"],
}


def _dil_bul(soru_kucuk):
    """Sorguda spesifik bir dil adı geçiyorsa, kurs başlıklarında aranacak
    Almanca dil adını döndürür (örn. 'almanca'/'german' -> 'Deutsch')."""
    for baslik_kelimesi, sorgu_kelimeleri in _DIL_SORGU_ANAHTARLARI.items():
        for kelime in sorgu_kelimeleri:
            if re.search(r"\b" + re.escape(kelime) + r"\b", soru_kucuk):
                return baslik_kelimesi
    return None

_LISTELEME_TETIKLEYICILERI = [
    "tüm", "tümü", "hepsi", "bütün", "listele", "liste",
    "all", "list", "alle", "sämtliche", "complete list",
]

_SEVIYE_DESENI = re.compile(r"\b([ABC][12](?:\.[12])?)\b", re.IGNORECASE)

_BASLAMAMIS_KELIMELERI = [
    "başlayacak", "yaklaşan", "yeni başla", "anstehend", "bevorstehend",
    "upcoming", "henüz başlamayan", "gelecek", "beginnen nach", "nach dem heutigen",
]

_DEVAM_EDEN_KELIMELERI = [
    "devam eden", "aktif", "şu an", "laufend", "aktuell laufend",
    "ongoing", "current", "currently running",
]

# --- YENİ: Ay eşleştirme (TR/DE/EN) ---
_AY_ESLESTIRME = {
    1: ["ocak", "januar", "january", "jan"],
    2: ["şubat", "subat", "februar", "february", "feb"],
    3: ["mart", "märz", "maerz", "march", "mär"],
    4: ["nisan", "april", "apr"],
    5: ["mayıs", "mayis", "mai", "may"],
    6: ["haziran", "juni", "june", "jun"],
    7: ["temmuz", "juli", "july", "jul"],
    8: ["ağustos", "agustos", "august", "aug"],
    9: ["eylül", "eylul", "september", "sept", "sep"],
    10: ["ekim", "oktober", "october", "okt", "oct"],
    11: ["kasım", "kasim", "november", "nov"],
    12: ["aralık", "aralik", "dezember", "december", "dez", "dec"],
}

_AY_ADLARI_TR = {
    1: "Ocak", 2: "Şubat", 3: "Mart", 4: "Nisan", 5: "Mayıs", 6: "Haziran",
    7: "Temmuz", 8: "Ağustos", 9: "Eylül", 10: "Ekim", 11: "Kasım", 12: "Aralık",
}


def _ay_bul(soru_kucuk):
    """Sorudan ay numarası çıkarır (word-boundary ile, 'email' içindeki 'mai' gibi
    yanlış eşleşmeleri önler). İlk eşleşen ayı döndürür."""
    for ay_no, kelimeler in _AY_ESLESTIRME.items():
        for kelime in kelimeler:
            if re.search(r"\b" + re.escape(kelime) + r"\b", soru_kucuk):
                return ay_no
    return None


def _kategori_bul(soru_kucuk):
    for kategori_adi, anahtar_kelimeler in _KATEGORI_ESLESTIRME.items():
        if any(ak in soru_kucuk for ak in anahtar_kelimeler):
            return kategori_adi
    return None


def _seviye_ve_durum_bul(soru, soru_kucuk):
    seviye_eslesme = _SEVIYE_DESENI.search(soru)
    seviye_kodu = seviye_eslesme.group(1).upper() if seviye_eslesme else None

    durum_filtresi = None
    if any(k in soru_kucuk for k in _BASLAMAMIS_KELIMELERI):
        durum_filtresi = "baslamamis"
    elif any(k in soru_kucuk for k in _DEVAM_EDEN_KELIMELERI):
        durum_filtresi = "devam_eden"

    return seviye_kodu, durum_filtresi


def _kategori_listesi_mi(soru):
    """'Tüm X kurslarını listele' tarzı AÇIK liste isteklerini yakalar.
    Eşleşirse (kategori_adi, seviye_kodu, durum_filtresi, ay_kodu) döner."""
    soru_kucuk = soru.lower()

    tetikleyici_var = any(t in soru_kucuk for t in _LISTELEME_TETIKLEYICILERI)
    kategori = _kategori_bul(soru_kucuk)

    if not tetikleyici_var or not kategori:
        return None

    seviye_kodu, durum_filtresi = _seviye_ve_durum_bul(soru, soru_kucuk)
    ay_kodu = _ay_bul(soru_kucuk)

    return (kategori, seviye_kodu, durum_filtresi, ay_kodu)


def _yapisal_filtre_sorgusu_mu(soru):
    """YENİ: Açık 'listele' kelimesi olmasa bile, kategori/dil + (seviye VEYA ay
    VEYA durum) sinyali varsa bunu yapısal (kesin) filtre sorgusu say.
    Örn: 'Gibt es einen Deutschkurs A1.1 im September?' -> kategori=Deutsch,
    seviye=A1.1, ay=9 -> yakalanır, embedding aramasına hiç girmez.

    dil_kodu (örn. 'Deutsch') bulunursa, kategori zaten "Deutsch und
    Fremdsprachen" olarak kabul edilir - ayrıca genel kategori kelimesi
    aramaya gerek kalmaz. Bu, 'almanca'/'german' gibi sorgu kelimelerinin
    kategori sözlüğünde eksik olması ihtimaline karşı bir güvenlik ağıdır."""
    soru_kucuk = soru.lower()

    dil_kodu = _dil_bul(soru_kucuk)
    kategori = _kategori_bul(soru_kucuk)

    if dil_kodu and not kategori:
        kategori = "Deutsch und Fremdsprachen"

    if not kategori:
        return None

    seviye_kodu, durum_filtresi = _seviye_ve_durum_bul(soru, soru_kucuk)
    ay_kodu = _ay_bul(soru_kucuk)

    # dil_kodu tek başına da yeterli bir sinyaldir (spesifik dil isteniyor demek
    # zaten hassasiyet gerektirir); diğerleri için en az bir ek filtre şart.
    if not (dil_kodu or seviye_kodu or ay_kodu or durum_filtresi):
        return None

    return (kategori, dil_kodu, seviye_kodu, ay_kodu, durum_filtresi)


def _metadatalari_filtrele(metadatalar, belgeler, seviye_kodu=None, durum_filtresi=None, ay_kodu=None, dil_kodu=None):
    """Ortak filtre mantığı: metadata+belge listelerini birlikte (senkron) filtreler."""
    ciftler = list(zip(metadatalar, belgeler))

    if dil_kodu:
        ciftler = [(m, b) for m, b in ciftler if dil_kodu.lower() in m["baslik"].lower()]

    if seviye_kodu:
        ciftler = [(m, b) for m, b in ciftler if seviye_kodu.lower() in m["baslik"].lower()]

    if durum_filtresi:
        ciftler = [
            (m, b) for m, b in ciftler
            if _durum_kodu(m.get("ilk_gun", ""), m.get("son_gun", "")) == durum_filtresi
        ]

    if ay_kodu:
        def _ay_uyuyor_mu(m):
            d = _tarihi_coz(m.get("ilk_gun", ""))
            return d is not None and d.month == ay_kodu
        ciftler = [(m, b) for m, b in ciftler if _ay_uyuyor_mu(m)]

    return ciftler


def _kategori_tam_listesi(kategori_adi, seviye_kodu=None, durum_filtresi=None, ay_kodu=None, dil_kodu=None):
    """Bir kategorideki kursları çeker, istenirse seviye/durum/ay/dil filtresi uygular.
    Deterministik Türkçe metin döner (AÇIK 'listele' isteği yolu için)."""
    sonuc = _koleksiyon.get(where={"kategori": kategori_adi})
    metadatalar = sonuc["metadatas"]
    belgeler = sonuc.get("documents", [None] * len(metadatalar))

    ciftler = _metadatalari_filtrele(metadatalar, belgeler, seviye_kodu, durum_filtresi, ay_kodu, dil_kodu)

    aciklama_parcalari = []
    if dil_kodu:
        aciklama_parcalari.append(f"dil: {dil_kodu}")
    if seviye_kodu:
        aciklama_parcalari.append(f"seviye: {seviye_kodu}")
    if ay_kodu:
        aciklama_parcalari.append(f"ay: {_AY_ADLARI_TR[ay_kodu]}")
    if durum_filtresi == "baslamamis":
        aciklama_parcalari.append("durum: henüz başlamamış")
    elif durum_filtresi == "devam_eden":
        aciklama_parcalari.append("durum: şu an devam ediyor")
    filtre_aciklamasi = f" ({', '.join(aciklama_parcalari)})" if aciklama_parcalari else ""

    if not ciftler:
        return f"'{kategori_adi}'{filtre_aciklamasi} kategorisinde/filtresinde kurs bulunamadı."

    satirlar = [f"'{kategori_adi}'{filtre_aciklamasi} kategorisinde {len(ciftler)} kurs bulundu:\n"]
    for m, _ in ciftler:
        durum = _durumu_hesapla(m.get("ilk_gun", ""), m.get("son_gun", ""))
        satirlar.append(f"• {m['baslik']} — {m['tarih']} — {durum}")

    return "\n".join(satirlar)


def _parca_metni(m, belge):
    durum = _durumu_hesapla(m.get("ilk_gun", ""), m.get("son_gun", ""))
    return (
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


def _baglam_olustur(sonuclar):
    """Embedding query() sonuçlarından (nested liste) context metni üretir."""
    parcalar = []
    for i in range(len(sonuclar["ids"][0])):
        m = sonuclar["metadatas"][0][i]
        belge = sonuclar["documents"][0][i]
        parcalar.append(_parca_metni(m, belge))
    return "\n---\n".join(parcalar)


def _yapisal_baglam_olustur(kategori_adi, dil_kodu=None, seviye_kodu=None, ay_kodu=None, durum_filtresi=None):
    """YENİ: `where` ile kesin kategori çekimi + Python'da dil/seviye/ay/durum filtresi.
    LLM'e verilecek context'i ve bunun 'TAM/KESİN sonuç' olduğu bilgisini üretir."""
    sonuc = _koleksiyon.get(where={"kategori": kategori_adi})
    metadatalar = sonuc["metadatas"]
    belgeler = sonuc.get("documents", [None] * len(metadatalar))

    ciftler = _metadatalari_filtrele(metadatalar, belgeler, seviye_kodu, durum_filtresi, ay_kodu, dil_kodu)

    filtre_ozeti = []
    if dil_kodu:
        filtre_ozeti.append(f"dil={dil_kodu}")
    if seviye_kodu:
        filtre_ozeti.append(f"seviye={seviye_kodu}")
    if ay_kodu:
        filtre_ozeti.append(f"ay={_AY_ADLARI_TR[ay_kodu]}")
    if durum_filtresi:
        filtre_ozeti.append(f"durum={durum_filtresi}")
    filtre_ozeti_str = ", ".join(filtre_ozeti) if filtre_ozeti else "yok"

    baslik = (
        f"[KESİN FİLTRE SONUCU - kategori='{kategori_adi}', filtreler: {filtre_ozeti_str}]\n"
        f"Bu, veritabanının TAMAMI üzerinde yapılmış kesin bir filtrelemenin sonucudur "
        f"(örneklem/embedding araması DEĞİLDİR).\n"
    )

    if not ciftler:
        return baslik + "SONUÇ: Bu kriterlere uyan HİÇBİR kurs veritabanında bulunmuyor (0 sonuç)."

    parcalar = [_parca_metni(m, b) for m, b in ciftler]
    return baslik + f"SONUÇ: {len(ciftler)} kurs bulundu.\n\n" + "\n---\n".join(parcalar)


def _ollamaya_sor(soru, baglam, kesin_filtre=False):
    bugun_str = date.today().strftime("%d.%m.%Y")

    if kesin_filtre:
        ornekleme_notu = (
            "ÖNEMLİ: Sana verilen kurs bilgisi, veritabanının TAMAMI üzerinde yapılmış "
            "KESİN bir filtrelemenin sonucudur - bir örneklem DEĞİLDİR. Eğer context "
            "'0 sonuç' diyorsa, kullanıcıya NET ve KESİN bir şekilde bu kriterlere uyan "
            "kursun veritabanında bulunmadığını söyle. 'belki vardır ama gösterilmedi' "
            "gibi belirsiz ifadeler KULLANMA - bu durumda kesinlik var."
        )
    else:
        ornekleme_notu = (
            "NOT: Sana verilen kurslar, TÜM veritabanından sadece en alakalı birkaç tanesidir; "
            "eğer sonuçlar arasında kullanıcının aradığı kriterlere uyan bir şey yoksa, bunun "
            "'veritabanında hiç böyle bir kurs olmadığı' anlamına gelmediğini, sadece 'bu örneklemde "
            "bulunamadığını' belirt."
        )

    sistem_talimati = (
        "Sen VHS Erftstadt (Halk Eğitim Merkezi) için çalışan bir bilgi asistanısın. "
        f"Bugünün tarihi {bugun_str}. "
        "Sana verilen kurs bilgilerine SADECE dayanarak kullanıcının sorusunu cevapla. "
        "Her kursun yanında verilen 'Durum' bilgisini OLDUĞU GİBİ kullan, kendin tarih hesaplaması YAPMA. "
        f"{ornekleme_notu} "
        "Kullanıcı hangi dilde soru sorduysa, cevabını da AYNI dilde ver. "
        "Cevabının TAMAMINI TEK bir dilde yaz; cümle ortasında başka bir dile GEÇME "
        "veya diller arasında karışık yazma. "
        "Verilen kurslar arasında, kullanıcının sorusuyla gerçekten alakalı OLMAYANLARI cevabına dahil etme. "
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
    # 1) AÇIK "tüm/listele" tarzı istekler -> deterministik Türkçe liste (mevcut davranış)
    liste_eslesme = _kategori_listesi_mi(soru)
    if liste_eslesme:
        kategori, seviye_kodu, durum_filtresi, ay_kodu = liste_eslesme
        return _kategori_tam_listesi(kategori, seviye_kodu, durum_filtresi, ay_kodu)

    # 2) YENİ: kategori/dil + (seviye VEYA ay VEYA durum) sinyali varsa
    #    -> embedding aramasına HİÇ girmeden `where` ile kesin filtrele, sonra LLM'e ver
    yapisal_eslesme = _yapisal_filtre_sorgusu_mu(soru)
    if yapisal_eslesme:
        kategori, dil_kodu, seviye_kodu, ay_kodu, durum_filtresi = yapisal_eslesme
        baglam = _yapisal_baglam_olustur(kategori, dil_kodu, seviye_kodu, ay_kodu, durum_filtresi)
        return _ollamaya_sor(soru, baglam, kesin_filtre=True)

    # 3) Fallback: klasik embedding araması
    soru_embedding = _embed_model.encode([soru]).tolist()
    sonuclar = _koleksiyon.query(query_embeddings=soru_embedding, n_results=KAC_SONUC)
    baglam = _baglam_olustur(sonuclar)
    return _ollamaya_sor(soru, baglam, kesin_filtre=False)
