# Aargauer Bibliografie × swisscovery — Matching-Liste

Erstellt eine Liste der Personen/Musikgruppen aus dem [Wikidata WikiProject Aargauer Bibliografie](https://www.wikidata.org/wiki/Wikidata:WikiProject_Aargauer_Bibliografie), die in [swisscovery](https://swisscovery.slsp.ch/) mindestens zwei nicht-selbstverlegte Buchtitel haben — als Grundlage für neue Wikipedia-Artikel.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
jupyter lab notebook.ipynb
```

Im Notebook von oben nach unten die Zellen ausführen. Der Vollabruf gegen swisscovery dauert ca. 5–15 min und cacht alle Rohdaten in `data/swisscovery_hits.json`, sodass Re-Runs schnell sind.

## Output

- `data/output/matching_liste.csv` — alle Personen mit Anzahl Treffer, Selbstverlags-Flags, Confidence, Wikipedia-Status
- `data/output/matching_liste.md` — Kurzliste qualifizierender Personen ohne dewiki-Artikel, fertig zum Posten auf der Wikidata-Projektseite

## Datenquellen

| Quelle | Endpoint | Auth |
|---|---|---|
| Wikidata | https://query.wikidata.org/sparql | nein |
| swisscovery (SLSP Network Zone) | https://swisscovery.slsp.ch/view/sru/41SLSP_NETWORK | nein |

Properties: `P5008` (on focus list of) = `Q131160831` (WikiProject Aargauer Bibliografie). GND-ID = `P227`.
