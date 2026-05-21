# Aargauer Bibliografie × swisscovery — Matching-Liste

Erstellt eine Liste der Personen/Musikgruppen aus dem [Wikidata WikiProject Aargauer Bibliografie](https://www.wikidata.org/wiki/Wikidata:WikiProject_Aargauer_Bibliografie), die in [swisscovery](https://swisscovery.slsp.ch/) mindestens **zwei verifizierte Autor:innen-/Schöpfer:innen-Treffer** haben (nicht-selbstverlegt) — als Grundlage für neue Wikipedia-Artikel. „Verifiziert" heisst: MARC-Haupteintrag (100/110/111) oder Zusatzeintrag (700/710/711) mit Relator-Code aus der Allow-Liste `aut, cre, cmp, ill` (konfigurierbar in `matching.py`). 700 ohne Relator-Code wird mitgezählt, aber als `books_unverified` separat ausgewiesen und nicht zur Qualifikation gerechnet. Herausgeber:innen-, Beiträger:innen-, Interview-, Adressat:innen- und Subjekt-Rollen zählen nicht. Hochschulschriften (MARC 502) und Privatdrucke gelten als Selbstverlag. Manifestations-Dubletten werden über normalisierten Titel/Jahr/Creator und ISBN zusammengefasst. Für Personen ohne GND (Name-Fuzzy-Pfad) wird MARC `100$d` gegen die Wikidata-Geburts-/Sterbejahre abgeglichen — fehlen Jahresangaben in MARC oder weichen sie ab, wird der Treffer verworfen (Homonym-Schutz).

## Setup

Benötigt **Python 3.10–3.13**

```bash
/opt/homebrew/bin/python3.13 -m venv .venv
source .venv/bin/activate
pip install -e .
jupyter lab notebook.ipynb
```

Im Notebook von oben nach unten die Zellen ausführen. Der Vollabruf gegen swisscovery dauert ca. 30-60 min und cacht alle Rohdaten in `data/swisscovery_hits.json`, sodass Re-Runs schnell sind.

> **Hinweis:** Das Cache-Schema enthält jetzt zusätzlich Lebensdaten je Creator (für den Homonym-Schutz). Vor dem nächsten Lauf `data/swisscovery_hits.json` löschen und den Vollabruf einmal neu ausführen — die Notebook-Zelle erkennt das auch automatisch und verwirft alten Cache.

## Output

- `data/output/matching_liste.csv` — alle Personen mit Anzahl Treffer, Selbstverlags-Flags, Confidence, Wikipedia-Status
- `data/output/matching_liste.md` — Kurzliste qualifizierender Personen ohne dewiki-Artikel, fertig zum Posten auf der Wikidata-Projektseite

## Datenquellen

| Quelle | Endpoint | Auth |
|---|---|---|
| Wikidata | https://query.wikidata.org/sparql | nein |
| swisscovery (abn, Default) | https://abn.swisscovery.ch/view/sru/41SLSP_ABN | nein |
| swisscovery (SLSP Network Zone, optional) | https://swisscovery.slsp.ch/view/sru/41SLSP_NETWORK | nein |

Endpunkt umschaltbar über `ACTIVE_ENDPOINT` (`"abn"` / `"nz"`) in `src/aargau_match/swisscovery.py`. Default ist `abn` (weniger Manifestations-Dubletten); `nz` bietet breitere Abdeckung, dafür mehr Dubletten.

Properties: `P5008` (on focus list of) = `Q131160831` (WikiProject Aargauer Bibliografie). GND-ID = `P227`.
