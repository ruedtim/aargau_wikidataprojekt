# Aargauer Bibliografie × swisscovery — Matching-Liste

Erstellt eine Liste der Personen/Musikgruppen aus dem [Wikidata WikiProject Aargauer Bibliografie](https://www.wikidata.org/wiki/Wikidata:WikiProject_Aargauer_Bibliografie), die in [swisscovery](https://swisscovery.slsp.ch/) mindestens zwei nicht-selbstverlegte Treffer haben, **in denen die Person als Autor:in/Schöpfer:in auftritt** (Rollen-Allow-Liste `aut, cre, cmp, ill`, konfigurierbar in `matching.py`) — als Grundlage für neue Wikipedia-Artikel. Herausgeber:innen-, Beiträger:innen-, Interview-, Adressat:innen- und Subjekt-Rollen zählen nicht. Hochschulschriften (MARC 502) und Privatdrucke gelten als Selbstverlag. Manifestations-Dubletten werden über normalisierten Titel/Jahr/Creator und ISBN zusammengefasst.

## Setup

Benötigt **Python 3.10–3.13**

```bash
/opt/homebrew/bin/python3.13 -m venv .venv
source .venv/bin/activate
pip install -e .
jupyter lab notebook.ipynb
```

Im Notebook von oben nach unten die Zellen ausführen. Der Vollabruf gegen swisscovery dauert ca. 30-60 min und cacht alle Rohdaten in `data/swisscovery_hits.json`, sodass Re-Runs schnell sind.

> **Hinweis:** Das Cache-Schema hat sich geändert (Rollen je Creator statt nur GND-Liste). Vor dem nächsten Lauf `data/swisscovery_hits.json` löschen und den Vollabruf einmal neu ausführen.

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
