import json

from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from core.models import Airplane, Airport
from core.tests.data import create_demo_data
from web.comparison import build_comparison
from web.templatetags.ui import coords, duration, flag


class WebTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.planes = create_demo_data()


class HomeTests(WebTestCase):
    def test_stats_and_examples(self):
        response = self.client.get(reverse("web:home"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["stats"], {"airports": 9, "countries": 5, "airplanes": 4})
        examples = response.context["examples"]
        self.assertEqual([example["airplane"] for example in examples], ["Airbus A320neo", "ATR 72-600"])
        self.assertEqual(examples[0]["url"], f"/map/?route=SVO,JFK&plane={self.planes['a320'].pk}")


class AirplaneViewsTests(WebTestCase):
    url = reverse("web:airplane_list")

    def names(self, params=None):
        return [plane.name for plane in self.client.get(self.url, params or {}).context["airplanes"]]

    def test_filters_and_sorting(self):
        self.assertEqual(len(self.names()), 4)
        self.assertEqual(self.names({"q": "boeing"}), ["Boeing 777-300ER"])
        self.assertEqual(self.names({"q": "leap"}), ["Airbus A320neo"])
        self.assertEqual(self.names({"status": "retired"}), ["Concorde"])
        self.assertEqual(self.names({"sort": "-max_distance"})[0], "Boeing 777-300ER")
        self.assertEqual(self.names({"sort": "-cruise_speed"})[0], "Concorde")
        self.assertEqual(len(self.names({"sort": "drop table", "status": "weird"})), 4)

    def test_detail(self):
        a320 = self.planes["a320"]
        response = self.client.get(reverse("web:airplane_detail", args=[a320.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(a320, response.context["similar"])
        reach = {item["title"]: item["nonstop"] for item in response.context["reach"]}
        self.assertEqual(
            reach,
            {
                "Москва — Сочи": True,
                "Москва — Дубай": True,
                "Москва — Нью-Йорк": False,
                "Москва — Лос-Анджелес": False,
                "Москва — Аделаида": False,
            },
        )
        self.assertContains(response, f"/map/?plane={a320.pk}")
        self.assertEqual(self.client.get(reverse("web:airplane_detail", args=[999])).status_code, 404)


class AirportViewsTests(WebTestCase):
    url = reverse("web:airport_list")

    def codes(self, params):
        return [airport.iata_code for airport in self.client.get(self.url, params).context["airports"]]

    def test_search_filter_and_sort(self):
        self.assertEqual(self.codes({"q": "jfk"}), ["JFK"])
        self.assertEqual(self.codes({"country": "us", "sort": "iata_code"}), ["HNL", "JFK", "LAX"])
        self.assertEqual(self.codes({"sort": "country"})[:2], ["ADL", "DXB"])

    def test_pagination_keeps_filters(self):
        Airport.objects.bulk_create(
            Airport(
                iata_code=f"Q{i:02d}"[:3].replace("0", "A"),
                name=f"Test {i:02d}",
                country="US",
                latitude=10,
                longitude=i,
            )
            for i in range(10, 40)
        )
        response = self.client.get(self.url, {"country": "US", "page": 2})
        self.assertEqual(response.context["page_obj"].number, 2)
        self.assertEqual(len(response.context["airports"]), 3)
        self.assertContains(response, "?country=US&amp;page=1")

    def test_country_options(self):
        options = self.client.get(self.url).context["country_options"]
        self.assertEqual([option["code"] for option in options], ["AU", "AE", "RU", "US", "FR"])
        self.assertEqual(options[2], {"code": "RU", "name": "Россия", "total": 3})

    def test_detail(self):
        response = self.client.get("/airports/svo/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([ref.iata_code for ref, _ in response.context["nearest"]][:2], ["LED", "AER"])
        self.assertEqual(response.context["map_data"]["airport"], [55.9726, 37.4146, "SVO"])

    def test_missing_airport_uses_custom_404(self):
        response = self.client.get("/airports/QQQ/")
        self.assertEqual(response.status_code, 404)
        self.assertContains(response, "Такого рейса нет", status_code=404)


class CompareTests(WebTestCase):
    url = reverse("web:compare")

    def test_ids_formats(self):
        a320, b777, atr, concorde = (self.planes[key].pk for key in ("a320", "b777", "atr", "concorde"))
        for params in ({"ids": f"{a320},{b777}"}, {"ids": [str(a320), str(b777)]}):
            with self.subTest(params=params):
                context = self.client.get(self.url, params).context
                self.assertEqual([plane.pk for plane in context["selected"]], [a320, b777])
                self.assertEqual(len(context["rows"]), 6)

        context = self.client.get(self.url, {"ids": f"{a320},{a320},abc,{b777},{atr},{concorde},999"}).context
        self.assertEqual([plane.pk for plane in context["selected"]], [a320, b777, atr])

    def test_needs_two_airplanes(self):
        context = self.client.get(self.url, {"ids": str(self.planes["a320"].pk)}).context
        self.assertEqual(context["rows"], [])
        self.assertEqual(len(context["slots"]), 3)


class ComparisonLogicTests(SimpleTestCase):
    def plane(self, **fields):
        defaults = {"name": "X", "capacity": 100, "consumption": 1000, "cruise_speed": 800, "max_distance": 5000}
        return Airplane(**{**defaults, **fields})

    def verdicts(self, rows, label):
        row = next(row for row in rows if row.metric.label == label)
        return [cell.verdict for cell in row.cells]

    def test_two_airplanes_only_best_is_marked(self):
        rows = build_comparison([self.plane(max_distance=6000), self.plane(max_distance=3000)])
        self.assertEqual(self.verdicts(rows, "Максимальная дальность"), ["best", ""])
        self.assertEqual(self.verdicts(rows, "Крейсерская скорость"), ["", ""])

    def test_three_airplanes_and_lower_is_better(self):
        rows = build_comparison(
            [self.plane(consumption=900), self.plane(consumption=1500), self.plane(consumption=1100, capacity=None)]
        )
        self.assertEqual(self.verdicts(rows, "Расход топлива"), ["best", "worst", ""])
        self.assertEqual(self.verdicts(rows, "Пассажировместимость"), ["", "", ""])
        capacity = next(row for row in rows if row.metric.label == "Пассажировместимость")
        self.assertEqual([cell.share for cell in capacity.cells], [1.0, 1.0, 0.0])


class PlannerTests(WebTestCase):
    def test_embedded_data(self):
        response = self.client.get(reverse("web:planner"), {"route": "SVO,JFK"})
        self.assertContains(response, '<script id="planner-data" type="application/json">')
        data = json.loads(json.dumps(response.context["planner_data"]))
        self.assertEqual(len(data["airports"]), 9)
        self.assertIn(["SVO", "Sheremetyevo", "RU", 55.9726, 37.4146], data["airports"])
        self.assertEqual(data["countries"]["RU"], "Россия")
        self.assertEqual([plane["name"] for plane in data["airplanes"]][-1], "Concorde")
        self.assertEqual(data["urls"]["route"], "/api/route/")
        self.assertEqual(data["maxWaypoints"], 8)


class TemplateTagTests(SimpleTestCase):
    def test_duration(self):
        self.assertEqual(duration(3.75), "3 ч 45 мин")
        self.assertEqual(duration(0.5), "30 мин")
        self.assertEqual(duration(2), "2 ч")
        self.assertEqual(duration(None), "—")

    def test_flag_and_coords(self):
        self.assertEqual(flag("ru"), "🇷🇺")
        self.assertEqual(flag("RUS"), "")
        self.assertEqual(coords(55.97261, 37.41461), "55.9726, 37.4146")
        self.assertEqual(coords(-1.5, 2, 1), "-1.5, 2.0")
