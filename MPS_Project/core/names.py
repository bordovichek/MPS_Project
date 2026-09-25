"""Приведение названий аэропортов из OpenAIP (ВСЕ ЗАГЛАВНЫЕ, обрезаны до 40 символов) к читаемому виду."""

import re

OPENAIP_NAME_LIMIT = 40

ABBREVIATIONS = frozenset({"AAF", "AF", "AFB", "ANG", "ARB", "ARPT", "IL", "NAS", "USAF"})
LOWERCASE_PARTICLES = frozenset({"and", "at", "da", "de", "del", "do", "na", "of"})
SHORT_FORMS = frozenset({"DR", "JR", "LT", "MC", "MR", "SR", "ST"})
TRUNCATION_COMPLETIONS = (
    "AIRPORT",
    "INTERNATIONAL",
    "REGIONAL",
    "MUNICIPAL",
    "FIELD",
    "COUNTY",
    "AIRFIELD",
    "STATION",
)

_WORD = re.compile(r"[^\W\d_]+(?:[.'][^\W\d_]+)*\.?", re.UNICODE)
_VOWELS = re.compile(r"[AEIOUYÀ-ÖØ-Ý]")


def _complete_truncated_word(name: str) -> str:
    head, _, last = name.rpartition(" ")
    if not head:
        return name
    for word in TRUNCATION_COMPLETIONS:
        if word.startswith(last) and word != last:
            return f"{head} {word}"
    return name


def _case_word(word: str, *, first: bool) -> str:
    bare = word.rstrip(".")
    if bare in ABBREVIATIONS or "." in bare:
        return word
    if bare in SHORT_FORMS:
        return word.capitalize()
    if len(bare) > 1 and not _VOWELS.search(bare):
        return word
    if not first and word.lower() in LOWERCASE_PARTICLES:
        return word.lower()
    if "'" in word:
        prefix, _, rest = word.partition("'")
        if len(prefix) == 1:
            return f"{prefix}'{rest.capitalize()}"
    return word.capitalize()


def normalize_airport_name(raw: str) -> str:
    name = " ".join(raw.split())
    if not name or name != name.upper():
        return name
    if len(name) == OPENAIP_NAME_LIMIT:
        name = _complete_truncated_word(name)

    parts: list[str] = []
    position = 0
    for index, match in enumerate(_WORD.finditer(name)):
        parts.append(name[position : match.start()])
        parts.append(_case_word(match.group(), first=index == 0))
        position = match.end()
    parts.append(name[position:])
    return "".join(parts)
