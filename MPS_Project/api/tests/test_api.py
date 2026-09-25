from unittest import mock

from django.core.cache import cache
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework.throttling import ScopedRateThrottle

from core.geo import haversine_km
from core.tests.data import create_demo_data


class ApiTestCase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.planes = create_demo_data()

    def setUp(self):
        cache.clear()


class CatalogApiTests(ApiTestCase):
    def test_root_lists_endpoints(self):
        response = self.client.get(reverse("api:root"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.data), {"airplanes", "airports", "route"})

    def test_airplanes(self):
        response = self.client.get(reverse("api:airplane-list"))
        planes = {plane["name"]: plane for plane in response.data}
        self.assertEqual(len(planes), 4)
        self.assertEqual(planes["Airbus A320neo"]["fuel_per_seat_100km"], round(2400 / (180 * 840) * 100, 2))

        retired = self.client.get(reverse("api:airplane-list"), {"in_service": "false"}).data
        self.assertEqual([plane["name"] for plane in retired], ["Concorde"])
        found = self.client.get(reverse("api:airplane-list"), {"search": "boeing"}).data
        self.assertEqual([plane["name"] for plane in found], ["Boeing 777-300ER"])

        detail = self.client.get(reverse("api:airplane-detail", args=[self.planes["atr"].pk]))
        self.assertEqual(detail.data["max_distance"], 1500)

    def test_airports_list_is_plain_unless_limit_given(self):
        response = self.client.get(reverse("api:airport-list"))
        self.assertIsInstance(response.data, list)
        self.assertEqual(len(response.data), 9)

        paginated = self.client.get(reverse("api:airport-list"), {"limit": 2, "offset": 2}).data
        self.assertEqual(paginated["count"], 9)
        self.assertEqual([airport["iata_code"] for airport in paginated["results"]], ["CDG", "DXB"])

    def test_airport_filters_and_detail(self):
        us = self.client.get(reverse("api:airport-list"), {"country": "us"}).data
        self.assertEqual([airport["iata_code"] for airport in us], ["HNL", "JFK", "LAX"])
        self.assertEqual(us[0]["country_name"], "США")

        found = self.client.get(reverse("api:airport-list"), {"search": "led"}).data
        self.assertEqual([airport["iata_code"] for airport in found], ["LED"])

        detail = self.client.get("/api/airports/svo/")
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.data["name"], "Sheremetyevo")
        self.assertEqual(self.client.get("/api/airports/XXX/").status_code, 404)


class RouteApiTests(ApiTestCase):
    url = reverse("api:route")

    def test_route_with_technical_stop(self):
        response = self.client.get(self.url, {"airports": "svo, jfk", "airplane": self.planes["a320"].pk})
        self.assertEqual(response.status_code, 200)
        data = response.data

        self.assertEqual([stop["iata_code"] for stop in data["stops"]], ["SVO", "CDG", "JFK"])
        self.assertEqual([stop["is_waypoint"] for stop in data["stops"]], [True, False, True])
        self.assertEqual(data["criterion"], "time")
        self.assertEqual(data["airplane"]["range_km"], 6300)
        self.assertEqual(data["summary"]["flights"], 2)
        self.assertEqual(data["summary"]["technical_stops"], 1)
        self.assertEqual(data["summary"]["ground_time_h"], 1.0)
        self.assertEqual(data["legs"][0]["origin"], "SVO")
        self.assertEqual(data["legs"][0]["path"][0], (55.9726, 37.4146))
        self.assertAlmostEqual(
            data["summary"]["distance_km"], sum(leg["distance_km"] for leg in data["legs"]), delta=0.2
        )

    def test_route_without_airplane_is_direct(self):
        response = self.client.get(self.url, {"airports": "SVO,JFK,LAX"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual([stop["iata_code"] for stop in response.data["stops"]], ["SVO", "JFK", "LAX"])
        self.assertIsNone(response.data["airplane"])
        self.assertIsNone(response.data["summary"]["total_time_h"])

    def test_validation_errors(self):
        cases = {
            "": {"airports": ""},
            "one airport": {"airports": "SVO"},
            "bad code": {"airports": "SVO,S1O"},
            "unknown": {"airports": "SVO,XXX"},
            "duplicate": {"airports": "SVO,SVO"},
            "airplane": {"airports": "SVO,LED", "airplane": 999},
            "criterion": {"airports": "SVO,LED", "criterion": "cheapest"},
        }
        for name, params in cases.items():
            with self.subTest(name):
                response = self.client.get(self.url, params)
                self.assertEqual(response.status_code, 400)
        response = self.client.get(self.url, {"airports": "SVO,XXX"})
        self.assertEqual(response.data["airports"], ["Аэропорты не найдены: XXX."])

    def test_unreachable_route_suggests_airplanes(self):
        response = self.client.get(self.url, {"airports": "SVO,HNL", "airplane": self.planes["atr"].pk})
        self.assertEqual(response.status_code, 422)
        atlantic = haversine_km(49.0097, 2.5479, 40.6398, -73.7789)
        self.assertEqual(response.data["required_range_km"], round(atlantic))
        self.assertEqual(response.data["gaps"][0]["origin"], "SVO")
        self.assertEqual(
            [plane["name"] for plane in response.data["suitable_airplanes"]],
            ["Airbus A320neo", "Boeing 777-300ER", "Concorde"],
        )
        self.assertIn("ATR 72-600", response.data["detail"])

    def test_throttling(self):
        with mock.patch.object(ScopedRateThrottle, "THROTTLE_RATES", {"route": "2/min"}):
            statuses = [self.client.get(self.url, {"airports": "SVO,LED"}).status_code for _ in range(3)]
        self.assertEqual(statuses, [200, 200, 429])
