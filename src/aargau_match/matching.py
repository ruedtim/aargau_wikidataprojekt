"""Match Wikidata persons against swisscovery hits, apply self-publishing heuristic."""

from __future__ import annotations

from dataclasses import dataclass

from rapidfuzz import fuzz

from .swisscovery import BookRecord, dedup_by_mms

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
]

NAME_MATCH_THRESHOLD = 85


def is_self_published(publisher: str) -> bool:
    if not publisher:
        return False
    p = publisher.lower()
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
    has_dewiki: bool
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
    return f"https://swisscovery.slsp.ch/discovery/search?query={q}&tab=41SLSP_NETWORK_CI&vid=41SLSP_NETWORK:LIBRARYNETWORK"


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

    # Drop hits where the person appears only as subject (MARC 600), not as creator (100/700).
    # If GND known: check creator_gnds. Otherwise: rely on name fuzzy match against author field.
    def is_creator(b: BookRecord) -> bool:
        if gnd:
            return gnd in b.creator_gnds
        if given or family:
            if name_matches(b.author, given, family):
                return True
            # check 700-field creators too via MARC author string — author here is only 100$a
            return False
        return True

    filtered = [b for b in raw_books if is_creator(b)]
    books = dedup_by_mms(filtered)
    selfpub = [b for b in books if is_self_published(b.publisher)]
    non_self = [b for b in books if not is_self_published(b.publisher)]
    qualifies = len(non_self) >= 2

    publishers = sorted({b.publisher for b in books if b.publisher})
    sample_titles = [b.title for b in non_self[:5] if b.title]

    requires_review = (
        confidence == "name-fuzzy"
        or (qualifies and len(non_self) == 2 and not person.get("gnd"))
    )

    return PersonResult(
        q_id=person["q_id"],
        name=name,
        gnd=person.get("gnd", ""),
        instance_of=person.get("instance_of", ""),
        birth=person.get("birth", ""),
        death=person.get("death", ""),
        books_total=len(books),
        books_non_selfpub=len(non_self),
        books_selfpub=len(selfpub),
        qualifies=qualifies,
        confidence=confidence,
        requires_review=requires_review,
        has_dewiki=bool(person.get("dewiki_url")),
        publishers="; ".join(publishers),
        sample_titles=" | ".join(sample_titles),
        wikidata_url=person.get("wikidata_url", f"https://www.wikidata.org/wiki/{person['q_id']}"),
        dewiki_url=person.get("dewiki_url", ""),
        swisscovery_search_url=_swisscovery_search_url(family, given, person.get("gnd", "")),
    )
