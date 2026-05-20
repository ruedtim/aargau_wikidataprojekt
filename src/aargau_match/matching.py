"""Match Wikidata persons against swisscovery hits, apply self-publishing heuristic."""

from __future__ import annotations

from dataclasses import dataclass

from rapidfuzz import fuzz

from .swisscovery import ACTIVE_ENDPOINT, BookRecord, dedup_works

SELFPUB_PUBLISHERS = [
    "bod",
    "books on demand",
    "epubli",
    "tredition",
    "norderstedt",
    "lulu",
    "tolino media",
    "neopubli",
    "everbook",
    "twentysix",
    "engelsdorfer",
    "novum pro",
    "novum publishing",
    "privatdruck",
    "selbstverlag",
    "eigenverlag",
    "im selbstverlag",
    "s.n.",
    "[s.n.]",
    "verfasser",
    "autor",
]

NAME_MATCH_THRESHOLD = 85

# Relator-Codes ($4/$e), die als Autor:in/Schöpfer:in zählen. Bewusst eng;
# bei Bedarf hier anpassen (z. B. "trl", "edt" ergänzen/entfernen).
AUTHOR_RELATORS = {"aut", "cre", "cmp", "ill"}
# Eindeutige Nicht-Autor-Rollen — schliessen auch einen Haupteintrag aus,
# wenn das die einzigen vorhandenen Relatoren sind.
NON_AUTHOR_RELATORS = {"edt", "hnr", "dte", "rcp", "ive", "ivr", "trl", "ctb"}
MAIN_ENTRY_TAGS = {"100", "110", "111"}
ADDED_ENTRY_TAGS = {"700", "710", "711"}


def is_self_published(book: BookRecord) -> bool:
    """Selbstverlag/Privatdruck oder Hochschulschrift (MARC 502)."""
    if book.is_thesis:
        return True
    p = (book.publisher or "").lower()
    if not p:
        return False
    return any(needle in p for needle in SELFPUB_PUBLISHERS)


def name_matches(book_author: str, given: str, family: str) -> bool:
    """Fuzzy compare a MARC author string ('Family, Given' or 'Given Family') to expected name."""
    if not book_author:
        return False
    expected_a = f"{given} {family}".strip()
    expected_b = f"{family}, {given}".strip(" ,")
    score = max(
        fuzz.token_sort_ratio(book_author, expected_a),
        fuzz.token_sort_ratio(book_author, expected_b),
    )
    return score >= NAME_MATCH_THRESHOLD


@dataclass
class PersonResult:
    q_id: str
    name: str
    gnd: str
    instance_of: str
    birth: str
    death: str
    books_total: int
    books_non_selfpub: int
    books_selfpub: int
    qualifies: bool
    confidence: str  # "gnd" | "name-fuzzy"
    requires_review: bool
    review_reason: str
    has_dewiki: bool
    books_thesis: int
    publishers: str
    sample_titles: str
    wikidata_url: str
    dewiki_url: str
    swisscovery_search_url: str

    def as_row(self) -> dict:
        from dataclasses import asdict

        return asdict(self)


def _swisscovery_search_url(family: str, given: str, gnd: str) -> str:
    if gnd:
        q = f"any,contains,{gnd}"
    else:
        q = f"creator,contains,{family} {given}".rstrip()
    if ACTIVE_ENDPOINT == "abn":
        return f"https://abn.swisscovery.ch/discovery/search?query={q}&tab=41SLSP_ABN&vid=41SLSP_ABN:abn"
    return f"https://swisscovery.slsp.ch/discovery/search?query={q}&tab=41SLSP_NETWORK_CI&vid=41SLSP_NETWORK:LIBRARYNETWORK"


def classify_authorship(
    book: BookRecord, person_gnd: str, given: str, family: str
) -> tuple[bool, bool]:
    """(zählt_als_autorenwerk, rolle_ungeprüft) für eine Person je Buch.

    Haupteintrag (100/110/111) zählt, ausser die einzigen Relatoren sind
    eindeutig Nicht-Autor. Zusatzeintrag (700/710/711) zählt nur mit
    Autor:innen-Relator; ohne jeden Relator zählt er, aber als ungeprüft.
    """
    matched = []
    for c in book.creators:
        if person_gnd:
            if c.get("gnd") == person_gnd:
                matched.append(c)
        elif given or family:
            if name_matches(c.get("name") or book.author, given, family):
                matched.append(c)
    if not person_gnd and not (given or family):
        return True, False
    if not matched:
        return False, False

    counts = False
    verified = False
    for c in matched:
        rels = set(c.get("relators") or [])
        tag = c.get("tag", "")
        if tag in MAIN_ENTRY_TAGS:
            if rels and not (rels & AUTHOR_RELATORS) and rels <= NON_AUTHOR_RELATORS:
                continue
            counts = True
            verified = True
        elif tag in ADDED_ENTRY_TAGS:
            if rels:
                if rels & AUTHOR_RELATORS:
                    counts = True
                    verified = True
            else:
                counts = True
    return counts, (counts and not verified)


def build_person_result(
    person: dict,
    raw_books: list[BookRecord],
    confidence: str,
) -> PersonResult:
    def _s(key: str) -> str:
        v = person.get(key)
        if v is None:
            return ""
        try:
            import math
            if isinstance(v, float) and math.isnan(v):
                return ""
        except Exception:
            pass
        return str(v).strip()

    given = _s("given")
    family = _s("family")
    gnd = _s("gnd")
    label = _s("label")
    name = label or f"{given} {family}".strip() or person["q_id"]

    # Nur Treffer behalten, in denen die Person als Autor:in/Schöpfer:in
    # auftritt (Rollen-Allow-Liste); Subjekt-/Herausgeber-/Adressat-Rollen raus.
    books = dedup_works(raw_books)
    role_unverified = False
    authored: list[BookRecord] = []
    for b in books:
        counts, unverified = classify_authorship(b, gnd, given, family)
        if counts:
            authored.append(b)
            role_unverified = role_unverified or unverified

    selfpub = [b for b in authored if is_self_published(b)]
    non_self = [b for b in authored if not is_self_published(b)]
    n_thesis = sum(1 for b in authored if b.is_thesis)
    qualifies = len(non_self) >= 2

    publishers = sorted({b.publisher for b in authored if b.publisher})
    sample_titles = [b.title for b in non_self[:5] if b.title]

    reasons = []
    if confidence == "name-fuzzy":
        reasons.append("name-fuzzy")
    if role_unverified:
        reasons.append("rolle-ungeprüft (700 ohne Relator)")
    if qualifies and len(non_self) == 2 and not gnd:
        reasons.append("genau 2, ohne GND")
    review_reason = "; ".join(reasons)
    requires_review = bool(reasons)

    return PersonResult(
        q_id=person["q_id"],
        name=name,
        gnd=person.get("gnd", ""),
        instance_of=person.get("instance_of", ""),
        birth=person.get("birth", ""),
        death=person.get("death", ""),
        books_total=len(authored),
        books_non_selfpub=len(non_self),
        books_selfpub=len(selfpub),
        qualifies=qualifies,
        confidence=confidence,
        requires_review=requires_review,
        review_reason=review_reason,
        has_dewiki=bool(person.get("dewiki_url")),
        books_thesis=n_thesis,
        publishers="; ".join(publishers),
        sample_titles=" | ".join(sample_titles),
        wikidata_url=person.get("wikidata_url", f"https://www.wikidata.org/wiki/{person['q_id']}"),
        dewiki_url=person.get("dewiki_url", ""),
        swisscovery_search_url=_swisscovery_search_url(family, given, person.get("gnd", "")),
    )
