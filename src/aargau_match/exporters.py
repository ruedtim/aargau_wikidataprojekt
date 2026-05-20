"""Write the matching list to CSV and Markdown."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

CSV_COLUMNS = [
    "q_id",
    "name",
    "gnd",
    "instance_of",
    "birth",
    "death",
    "books_total",
    "books_non_selfpub",
    "books_selfpub",
    "qualifies",
    "confidence",
    "requires_review",
    "review_reason",
    "has_dewiki",
    "books_thesis",
    "publishers",
    "sample_titles",
    "wikidata_url",
    "dewiki_url",
    "swisscovery_search_url",
]


def sort_results(df: pd.DataFrame) -> pd.DataFrame:
    return df.sort_values(
        ["qualifies", "books_non_selfpub", "name"],
        ascending=[False, False, True],
    ).reset_index(drop=True)


def to_csv(df: pd.DataFrame, path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    out = sort_results(df)[CSV_COLUMNS]
    out.to_csv(path, index=False, encoding="utf-8")
    return path


def to_markdown(df: pd.DataFrame, path: str | Path) -> Path:
    """Write a Markdown table — only qualifying persons without a dewiki article."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    sub = df[(df["qualifies"]) & (~df["has_dewiki"])].copy()
    sub = sort_results(sub)

    lines = [
        "# Vorschlagsliste neue Wikipedia-Artikel — Aargauer Bibliografie",
        "",
        f"Stand: automatisch generiert. {len(sub)} Personen mit ≥2 nicht-selbstverlegten Treffern in swisscovery, in denen die Person als Autor:in/Schöpfer:in auftritt, und (noch) ohne dewiki-Artikel.",
        "",
        "| Person | GND | Bücher (non-selfpub) | Confidence | Review-Grund | Wikidata | swisscovery |",
        "|---|---|---:|---|---|---|---|",
    ]
    for _, r in sub.iterrows():
        review_mark = " ⚠️" if r["requires_review"] else ""
        gnd_cell = (
            f"[{r['gnd']}](https://d-nb.info/gnd/{r['gnd']})" if r["gnd"] else "—"
        )
        lines.append(
            f"| {r['name']}{review_mark} "
            f"| {gnd_cell} "
            f"| {r['books_non_selfpub']} "
            f"| {r['confidence']} "
            f"| {r['review_reason'] or '—'} "
            f"| [{r['q_id']}]({r['wikidata_url']}) "
            f"| [Suche]({r['swisscovery_search_url']}) |"
        )
    lines.append("")
    lines.append("⚠️ = manuelle Kontrolle empfohlen: Treffer nur per Namens-Fuzzy-Matching, oder Rolle ungeprüft (700 ohne Relator-Code), oder genau 2 Treffer ohne GND. Hochschulschriften (MARC 502) und Privatdrucke zählen als Selbstverlag.")
    path.write_text("\n".join(lines), encoding="utf-8")
    return path
