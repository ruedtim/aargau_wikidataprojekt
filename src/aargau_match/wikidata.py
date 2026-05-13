"""Fetch the Aargauer Bibliografie focus list from Wikidata via SPARQL."""

from __future__ import annotations

import pandas as pd
from SPARQLWrapper import JSON, SPARQLWrapper

WIKIDATA_SPARQL = "https://query.wikidata.org/sparql"
USER_AGENT = "AargauerBibliografie-Matching/0.1 (https://github.com/stazh)"

FOCUS_QUERY = """
SELECT DISTINCT ?item ?itemLabel ?given ?family ?gnd ?instanceOfLabel ?birth ?death ?dewiki WHERE {
  ?item wdt:P5008 wd:Q131160831 .
  OPTIONAL { ?item wdt:P227 ?gnd }
  OPTIONAL { ?item wdt:P735 ?gn . ?gn rdfs:label ?given FILTER(LANG(?given) = "de") }
  OPTIONAL { ?item wdt:P734 ?fn . ?fn rdfs:label ?family FILTER(LANG(?family) = "de") }
  OPTIONAL { ?item wdt:P31  ?io . ?io rdfs:label ?instanceOfLabel FILTER(LANG(?instanceOfLabel) = "de") }
  OPTIONAL { ?item wdt:P569 ?birth }
  OPTIONAL { ?item wdt:P570 ?death }
  OPTIONAL {
    ?dewiki schema:about ?item ;
            schema:isPartOf <https://de.wikipedia.org/> .
  }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "de,en" }
}
"""


def fetch_focus_list() -> pd.DataFrame:
    """Fetch all Wikidata items with P5008 = Q131160831 (WikiProject Aargauer Bibliografie)."""
    sparql = SPARQLWrapper(WIKIDATA_SPARQL, agent=USER_AGENT)
    sparql.setQuery(FOCUS_QUERY)
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()

    rows = []
    for b in results["results"]["bindings"]:
        rows.append(
            {
                "q_id": b["item"]["value"].rsplit("/", 1)[-1],
                "label": b.get("itemLabel", {}).get("value", ""),
                "given": b.get("given", {}).get("value", ""),
                "family": b.get("family", {}).get("value", ""),
                "gnd": b.get("gnd", {}).get("value", ""),
                "instance_of": b.get("instanceOfLabel", {}).get("value", ""),
                "birth": b.get("birth", {}).get("value", "")[:10],
                "death": b.get("death", {}).get("value", "")[:10],
                "dewiki_url": b.get("dewiki", {}).get("value", ""),
            }
        )

    df = pd.DataFrame(rows)
    # Collapse duplicate Q-IDs (multiple instance_of values etc.) — keep first non-empty
    df = (
        df.groupby("q_id", as_index=False)
        .agg(
            {
                "label": "first",
                "given": "first",
                "family": "first",
                "gnd": "first",
                "instance_of": lambda s: " / ".join(sorted({v for v in s if v})),
                "birth": "first",
                "death": "first",
                "dewiki_url": "first",
            }
        )
    )
    df["has_dewiki"] = df["dewiki_url"].astype(bool)
    df["wikidata_url"] = "https://www.wikidata.org/wiki/" + df["q_id"]
    return df
