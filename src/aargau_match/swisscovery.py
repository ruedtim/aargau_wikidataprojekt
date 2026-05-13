"""Client for the swisscovery (SLSP Network Zone) SRU endpoint.

Endpoint is open (no API key). Returns MARC21-XML.
"""

from __future__ import annotations

import io
import time
from dataclasses import asdict, dataclass
from typing import Iterable

import requests
from pymarc import parse_xml_to_array

SRU_BASE = "https://swisscovery.slsp.ch/view/sru/41SLSP_NETWORK"
PAGE_SIZE = 50
SAFETY_CAP = 200  # max hits collected per person
THROTTLE_SECONDS = 0.2
TIMEOUT = 60

SRU_NS = {
    "srw": "http://www.loc.gov/zing/srw/",
    "marc": "http://www.loc.gov/MARC21/slim",
}


@dataclass
class BookRecord:
    mms_id: str
    title: str
    author: str
    year: str
    publisher: str
    isbn: str
    language: str
    creator_gnds: list[str]   # GNDs from MARC 100$0 / 700$0
    subject_gnds: list[str]   # GNDs from MARC 600$0

    def to_dict(self) -> dict:
        return asdict(self)


def _extract_gnds(field) -> list[str]:
    """Pull GND IDs out of subfield $0 entries like '(DE-588)118031198'."""
    if field is None:
        return []
    out = []
    for sub in field.get_subfields("0"):
        if not sub:
            continue
        s = sub.strip()
        if s.startswith("(DE-588)"):
            out.append(s[len("(DE-588)"):])
        elif s.startswith("http") and "gnd/" in s:
            out.append(s.rsplit("/", 1)[-1])
    return out


def _http_get(params: dict, retries: int = 3) -> bytes:
    last_exc: Exception | None = None
    for attempt in range(retries):
        try:
            r = requests.get(SRU_BASE, params=params, timeout=TIMEOUT)
            if r.status_code in (429, 503):
                time.sleep(2 ** attempt)
                continue
            r.raise_for_status()
            return r.content
        except requests.RequestException as exc:
            last_exc = exc
            time.sleep(2 ** attempt)
    raise RuntimeError(f"SRU request failed after {retries} attempts: {last_exc}")


def _parse_marc(xml_bytes: bytes) -> list[BookRecord]:
    """Extract MARC records from an SRU response and map to BookRecord."""
    # pymarc.parse_xml_to_array expects a file-like object containing the MARC collection.
    # SLSP's SRU wraps records in srw:recordData/marc:record. We pull each marc:record out.
    import xml.etree.ElementTree as ET

    root = ET.fromstring(xml_bytes)
    records_xml = root.findall(".//marc:record", SRU_NS)
    if not records_xml:
        return []

    # Build a synthetic MARC collection for pymarc
    collection = ET.Element("{http://www.loc.gov/MARC21/slim}collection")
    for rec in records_xml:
        collection.append(rec)
    buf = io.BytesIO(ET.tostring(collection, encoding="utf-8"))
    pymarc_records = parse_xml_to_array(buf)

    out: list[BookRecord] = []
    for rec in pymarc_records:
        mms_id = ""
        f001 = rec.get("001")
        if f001 is not None:
            mms_id = (f001.data or "").strip()

        title = ""
        f245 = rec.get("245")
        if f245 is not None:
            parts = []
            for sf in ("a", "b"):
                v = f245.get(sf)
                if v:
                    parts.append(v.strip(" /:,"))
            title = " : ".join(p for p in parts if p)

        author = ""
        f100 = rec.get("100")
        if f100 is not None:
            author = (f100.get("a") or "").strip(" ,.")

        year = ""
        publisher = ""
        f264 = rec.get("264")
        f260 = rec.get("260")
        f_pub = f264 or f260
        if f_pub is not None:
            year = (f_pub.get("c") or "").strip(" .,[]")
            publisher = (f_pub.get("b") or "").strip(" ,.")

        isbn = ""
        f020 = rec.get("020")
        if f020 is not None:
            isbn = (f020.get("a") or "").split(" ")[0].strip()

        language = ""
        f041 = rec.get("041")
        if f041 is not None:
            language = (f041.get("a") or "").strip()
        if not language:
            f008 = rec.get("008")
            if f008 is not None and f008.data and len(f008.data) >= 38:
                language = f008.data[35:38]

        creator_gnds: list[str] = []
        for f in rec.get_fields("100", "110", "111", "700", "710", "711"):
            creator_gnds.extend(_extract_gnds(f))
        subject_gnds: list[str] = []
        for f in rec.get_fields("600", "610", "611"):
            subject_gnds.extend(_extract_gnds(f))

        out.append(
            BookRecord(
                mms_id=mms_id,
                title=title,
                author=author,
                year=year,
                publisher=publisher,
                isbn=isbn,
                language=language,
                creator_gnds=creator_gnds,
                subject_gnds=subject_gnds,
            )
        )
    return out


def _diagnostics(xml_bytes: bytes) -> str | None:
    """Return SRU diagnostic message if present, else None."""
    import xml.etree.ElementTree as ET

    root = ET.fromstring(xml_bytes)
    diag = root.find(".//{http://www.loc.gov/zing/srw/diagnostic/}message")
    if diag is not None and diag.text:
        return diag.text
    return None


def _search(cql: str) -> list[BookRecord]:
    collected: list[BookRecord] = []
    start = 1
    while True:
        params = {
            "version": "1.2",
            "operation": "searchRetrieve",
            "query": cql,
            "maximumRecords": PAGE_SIZE,
            "startRecord": start,
            "recordSchema": "marcxml",
        }
        xml_bytes = _http_get(params)
        recs = _parse_marc(xml_bytes)
        if not recs:
            break
        collected.extend(recs)
        if len(recs) < PAGE_SIZE or len(collected) >= SAFETY_CAP:
            break
        start += PAGE_SIZE
        time.sleep(THROTTLE_SECONDS)
    return collected[:SAFETY_CAP]


def search_by_gnd(gnd: str, material: str = "BK") -> list[BookRecord]:
    """Search for books linked to a GND authority ID."""
    cql = f'alma.authority_id="(DE-588){gnd}" AND alma.mms_materialType={material}'
    return _search(cql)


def search_by_name(family: str, given: str, material: str = "BK") -> list[BookRecord]:
    """Search for books by author name (Nachname, Vorname)."""
    name = f"{family}, {given}".strip(" ,")
    if not name:
        return []
    cql = f'alma.creator="{name}" AND alma.mms_materialType={material}'
    return _search(cql)


def dedup_by_mms(records: Iterable[BookRecord]) -> list[BookRecord]:
    seen: set[str] = set()
    out: list[BookRecord] = []
    for r in records:
        key = r.mms_id or f"{r.title}|{r.year}"
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out
