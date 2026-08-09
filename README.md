# VHS Erftstadt Kursdaten-Extraktor

Ein Python-Tool zur automatisierten Erfassung von Kursdaten der Volkshochschule (VHS) Erftstadt. Das Projekt sammelt strukturierte Informationen (Titel, Termin, Ort, Beschreibung, Gebühr, Dauer, Kursleitung) von der öffentlichen VHS-Website und bereitet sie für die Weiterverarbeitung auf – als Grundlage für ein geplantes mehrsprachiges Chatbot-Projekt (Deutsch, Englisch, Türkisch).

## Hintergrund

Dieses Projekt ist Teil meines persönlichen KI-Lernportfolios. Ziel ist es, praktische Erfahrung mit Web-Scraping, Datenaufbereitung und (in einem späteren Schritt) Retrieval-Augmented Generation (RAG) zu sammeln – mit einem realen, lokalen Anwendungsfall.

## Funktionsweise

Das Projekt besteht aus drei aufeinander aufbauenden Skripten:

1. **`scraper_full.py`** – Findet automatisch alle Kurskategorien der VHS-Website, durchläuft alle Seiten und sammelt Basisdaten (Titel, Termin, Ort, Kursnummer, Link) zu jedem Kurs.
2. **`kurs_detay.py`** – Besucht die Detailseite jedes einzelnen Kurses und ergänzt Beschreibungstext, Gebühr, Dauer, Kursleitung und Gruppengröße. Unterstützt Fortsetzung nach Unterbrechung.
3. **Datenbereinigung** – Entfernt HTML-Artefakte (z. B. `&reg;`) und normalisiert den Text für die Weiterverarbeitung.

## Verwendete Technologien

- Python 3.12
- `requests` – HTTP-Anfragen
- `BeautifulSoup4` – HTML-Parsing
- `json` – Datenspeicherung

## Hinweis zu den Daten

Dieses Repository enthält **nur den Quellcode**, keine vollständigen Kursdaten. Die gesammelten Daten stammen von der öffentlichen Website der VHS Erftstadt (vhs-erftstadt.de) und werden hier aus urheberrechtlichen Gründen nicht veröffentlicht. Dies ist kein offizielles Projekt der VHS Erftstadt.

## Nächste Schritte

- Aufbau eines Retrieval-Systems (Embeddings + Vektorsuche) zur Beantwortung von Nutzeranfragen
- Integration in einen mehrsprachigen Telegram-Bot (Deutsch / Englisch / Türkisch)

## Autor

Yavuz — im Rahmen der beruflichen Weiterbildung im Bereich KI/IT.
