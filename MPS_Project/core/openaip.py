"""Импорт аэропортов из OpenAIP (https://www.openaip.net)."""

import logging
from collections.abc import Iterator
from dataclasses import dataclass

import requests
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction

from core.models import Airport, iata_validator
from core.names import normalize_airport_name

logger = logging.getLogger(__name__)

API_URL = "https://api.core.openaip.net/api/airports"
PAGE_LIMIT = 1000
TIMEOUT_S = 30


class OpenAIPError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class ImportResult:
    received: int
    saved: int
    skipped: int


def fetch_airports(country: str, *, api_key: str | None = None, max_pages: int | None = None) -> Iterator[dict]:
    api_key = api_key or settings.OPENAIP_API_KEY
    if not api_key:
        raise OpenAIPError("Не задан OPENAIP_API_KEY.")

    with requests.Session() as session:
        session.headers["x-openaip-api-key"] = api_key
        page = 1
        while True:
            try:
                response = session.get(
                    API_URL, params={"country": country, "page": page, "limit": PAGE_LIMIT}, timeout=TIMEOUT_S
                )
                response.raise_for_status()
                payload = response.json()
            except (requests.RequestException, ValueError) as error:
                raise OpenAIPError(f"Ошибка запроса к OpenAIP: {error}") from error

            yield from payload.get("items", [])
            last_page = payload.get("totalPages", 1)
            if page >= last_page or (max_pages and page >= max_pages):
                return
            page += 1


def parse_airport(item: dict) -> Airport | None:
    """Аэропорт из элемента ответа OpenAIP; None, если нет IATA-кода или данные некорректны."""
    try:
        code = (item.get("iataCode") or "").strip().upper()
        iata_validator(code)
        longitude, latitude = (float(value) for value in item["geometry"]["coordinates"][:2])
        country, name = item["country"].strip().upper(), normalize_airport_name(item["name"])
        if not (-90 <= latitude <= 90 and -180 <= longitude <= 180 and len(country) == 2 and name):
            raise ValueError("координаты, страна или название вне допустимых значений")
    except (KeyError, IndexError, TypeError, ValueError, AttributeError, ValidationError) as error:
        logger.debug("Пропущен аэропорт %s: %s", item.get("name"), error)
        return None
    return Airport(iata_code=code, name=name, country=country, latitude=latitude, longitude=longitude)


def import_airports(
    country: str, *, max_pages: int | None = None, dry_run: bool = False, api_key: str | None = None
) -> ImportResult:
    """Загружает аэропорты страны; существующие (по IATA-коду) обновляет, описание не трогает."""
    received, airports = 0, {}
    for item in fetch_airports(country.upper(), api_key=api_key, max_pages=max_pages):
        received += 1
        if airport := parse_airport(item):
            airports[airport.iata_code] = airport

    if not dry_run and airports:
        with transaction.atomic():
            Airport.objects.bulk_create(
                airports.values(),
                update_conflicts=True,
                unique_fields=["iata_code"],
                update_fields=["name", "country", "latitude", "longitude", "updated_at"],
                batch_size=500,
            )
    return ImportResult(received=received, saved=len(airports), skipped=received - len(airports))
