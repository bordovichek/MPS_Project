from io import StringIO
from unittest import mock

import requests
from django.core.management import CommandError, call_command
from django.test import SimpleTestCase, TestCase, override_settings

from core.models import Airport
from core.openaip import OpenAIPError, fetch_airports, import_airports, parse_airport


def item(code="SVO", name="SHEREMETYEVO INTERNATIONAL AIRPORT", lon=37.41, lat=55.97, country="RU"):
    return {
        "iataCode": code,
        "name": name,
        "country": country,
        "geometry": {"type": "Point", "coordinates": [lon, lat]},
    }


def page(items, page_number=1, total_pages=1):
    response = mock.Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {"items": items, "page": page_number, "totalPages": total_pages}
    return response


class ParseAirportTests(SimpleTestCase):
    def test_valid_item(self):
        airport = parse_airport(item(code="svo"))
        self.assertEqual(airport.iata_code, "SVO")
        self.assertEqual(airport.name, "Sheremetyevo International Airport")
        self.assertEqual((airport.latitude, airport.longitude), (55.97, 37.41))

    def test_invalid_items_are_skipped(self):
        broken = [
            item(code=""),
            item(code="SV0"),
            {**item(), "iataCode": None},
            {**item(), "geometry": {}},
            item(lat=95),
            item(country="RUS"),
            {"iataCode": "SVO"},
        ]
        for value in broken:
            with self.subTest(item=value):
                self.assertIsNone(parse_airport(value))


@override_settings(OPENAIP_API_KEY="secret")
class FetchAirportsTests(SimpleTestCase):
    def test_pages_are_followed(self):
        responses = [page([item("AAA")], 1, 2), page([item("BBB")], 2, 2)]
        with mock.patch("core.openaip.requests.Session.get", side_effect=responses) as get:
            codes = [entry["iataCode"] for entry in fetch_airports("RU")]
        self.assertEqual(codes, ["AAA", "BBB"])
        self.assertEqual(get.call_args.kwargs["params"], {"country": "RU", "page": 2, "limit": 1000})

    def test_max_pages(self):
        with mock.patch("core.openaip.requests.Session.get", return_value=page([item()], 1, 5)) as get:
            list(fetch_airports("RU", max_pages=1))
        self.assertEqual(get.call_count, 1)

    def test_errors(self):
        failing = mock.patch("core.openaip.requests.Session.get", side_effect=requests.ConnectionError("down"))
        with failing, self.assertRaises(OpenAIPError):
            list(fetch_airports("RU"))
        with override_settings(OPENAIP_API_KEY=""), self.assertRaises(OpenAIPError):
            list(fetch_airports("RU"))


class ImportAirportsTests(TestCase):
    def setUp(self):
        Airport.objects.create(
            iata_code="SVO", name="Old name", country="RU", latitude=0, longitude=0, description="Оставить как есть"
        )

    def run_import(self, items, **kwargs):
        with mock.patch("core.openaip.fetch_airports", return_value=iter(items)):
            return import_airports("ru", **kwargs)

    def test_upsert(self):
        result = self.run_import([item(), item(code="LED", name="PULKOVO AIRPORT", lat=59.8, lon=30.26), item(code="")])
        self.assertEqual((result.received, result.saved, result.skipped), (3, 2, 1))

        svo = Airport.objects.get(iata_code="SVO")
        self.assertEqual(svo.name, "Sheremetyevo International Airport")
        self.assertEqual(svo.latitude, 55.97)
        self.assertEqual(svo.description, "Оставить как есть")
        self.assertTrue(Airport.objects.filter(iata_code="LED", name="Pulkovo Airport").exists())

    def test_dry_run_changes_nothing(self):
        result = self.run_import([item(code="LED")], dry_run=True)
        self.assertEqual(result.saved, 1)
        self.assertFalse(Airport.objects.filter(iata_code="LED").exists())

    def test_management_command(self):
        stdout = StringIO()
        with mock.patch("core.openaip.fetch_airports", return_value=iter([item(code="LED")])):
            call_command("import_airports", "ru", stdout=stdout)
        self.assertIn("RU: получено 1, сохранено 1", stdout.getvalue())
        self.assertTrue(Airport.objects.filter(iata_code="LED").exists())

        with self.assertRaises(CommandError):
            call_command("import_airports", "RUS")
        with (
            mock.patch("core.openaip.fetch_airports", side_effect=OpenAIPError("нет ключа")),
            self.assertRaises(CommandError),
        ):
            call_command("import_airports", "RU")
