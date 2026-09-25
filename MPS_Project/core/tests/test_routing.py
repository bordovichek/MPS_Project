import heapq
import random
from itertools import pairwise

from django.test import SimpleTestCase, TestCase, override_settings

from core.geo import haversine_km
from core.models import Airport
from core.routing import (
    LEG_OVERHEAD_H,
    TURNAROUND_H,
    AirportIndex,
    Criterion,
    FlightProfile,
    InvalidRouteError,
    RouteUnreachableError,
    UnknownAirportsError,
    find_path,
    plan_route,
    required_range_km,
)


def make_index(points: dict[str, tuple[float, float]]) -> AirportIndex:
    return AirportIndex((code, f"Airport {code}", "RU", lat, lon) for code, (lat, lon) in points.items())


# A и G на экваторе в ~3336 км; C1, C2 лежат ровно на линии (три перелёта, путь короче),
# B чуть в стороне (два перелёта, путь длиннее). Так три критерия дают разные ответы.
LAYOUT = {"A": (0, 0), "C1": (0, 10), "B": (1.5, 15), "C2": (0, 20), "G": (0, 30)}
PROFILE = FlightProfile(range_km=2000, speed_kmh=800, fuel_burn_kg_h=2500)


def codes(plan) -> list[str]:
    return [stop.airport.iata_code for stop in plan.stops]


class CriteriaTests(SimpleTestCase):
    def setUp(self):
        self.index = make_index(LAYOUT)

    def test_shortest_distance_takes_more_hops(self):
        plan = plan_route(["A", "G"], PROFILE, Criterion.DISTANCE, index=self.index)
        self.assertEqual(codes(plan), ["A", "C1", "C2", "G"])

    def test_fewest_stops(self):
        plan = plan_route(["A", "G"], PROFILE, Criterion.STOPS, index=self.index)
        self.assertEqual(codes(plan), ["A", "B", "G"])

    def test_fastest_accounts_for_landing_overhead(self):
        plan = plan_route(["A", "G"], PROFILE, Criterion.TIME, index=self.index)
        self.assertEqual(codes(plan), ["A", "B", "G"])

    def test_direct_flight_when_in_range(self):
        long_range = FlightProfile(range_km=5000, speed_kmh=900, fuel_burn_kg_h=5000)
        for criterion in Criterion:
            with self.subTest(criterion=criterion):
                plan = plan_route(["A", "G"], long_range, criterion, index=self.index)
                self.assertEqual(codes(plan), ["A", "G"])

    def test_criterion_accepts_plain_string(self):
        plan = plan_route(["A", "G"], PROFILE, "stops", index=self.index)
        self.assertIs(plan.criterion, Criterion.STOPS)


class PlanTests(SimpleTestCase):
    def setUp(self):
        self.index = make_index(LAYOUT)

    def test_waypoints_and_technical_stops_are_marked(self):
        plan = plan_route(["A", "G", "A"], PROFILE, Criterion.STOPS, index=self.index)
        self.assertEqual(codes(plan), ["A", "B", "G", "B", "A"])
        self.assertEqual([stop.is_waypoint for stop in plan.stops], [True, False, True, False, True])
        self.assertEqual(plan.technical_stops, 2)

    @override_settings(JET_FUEL_PRICE_USD_PER_KG=1.0)
    def test_time_fuel_and_cost(self):
        plan = plan_route(["A", "G"], PROFILE, Criterion.STOPS, index=self.index)
        distances = [haversine_km(*LAYOUT[a], *LAYOUT[b]) for a, b in pairwise(["A", "B", "G"])]
        flight_time = sum(d / PROFILE.speed_kmh + LEG_OVERHEAD_H for d in distances)

        self.assertAlmostEqual(plan.distance_km, sum(distances), places=6)
        self.assertAlmostEqual(plan.max_leg_km, max(distances), places=6)
        self.assertAlmostEqual(plan.flight_time_h, flight_time, places=9)
        self.assertEqual(plan.ground_time_h, TURNAROUND_H)
        self.assertAlmostEqual(plan.total_time_h, flight_time + TURNAROUND_H, places=9)
        self.assertAlmostEqual(plan.fuel_kg, flight_time * PROFILE.fuel_burn_kg_h, places=6)
        self.assertAlmostEqual(plan.fuel_cost_usd, plan.fuel_kg, places=6)

    def test_without_airplane_flights_are_direct(self):
        plan = plan_route(["A", "G", "C1"], index=self.index)
        self.assertEqual(codes(plan), ["A", "G", "C1"])
        self.assertIs(plan.criterion, Criterion.DISTANCE)
        self.assertIsNone(plan.total_time_h)
        self.assertIsNone(plan.fuel_cost_usd)

    def test_leg_path_follows_great_circle(self):
        plan = plan_route(["A", "G"], index=self.index)
        path = plan.legs[0].path(step_km=500)
        self.assertEqual(path[0], (0.0, 0.0))
        self.assertEqual(path[-1], (0.0, 30.0))
        self.assertEqual(len(path), 8)

    def test_validation(self):
        with self.assertRaises(InvalidRouteError):
            plan_route(["A"], PROFILE, index=self.index)
        with self.assertRaises(InvalidRouteError):
            plan_route(["A", "A", "G"], PROFILE, index=self.index)
        with self.assertRaises(InvalidRouteError):
            plan_route(["A", "G"] * 5, PROFILE, index=self.index)
        with self.assertRaises(UnknownAirportsError) as error:
            plan_route(["A", "XXX", "YYY"], PROFILE, index=self.index)
        self.assertEqual(error.exception.codes, ["XXX", "YYY"])


class UnreachableTests(SimpleTestCase):
    def test_required_range_is_the_bottleneck_leg(self):
        index = make_index({"A": (0, 0), "D": (0, 10), "G": (0, 30)})
        with self.assertRaises(RouteUnreachableError) as error:
            plan_route(["A", "G"], FlightProfile(1500, 800, 1000), index=index)
        expected = haversine_km(0, 10, 0, 30)
        self.assertAlmostEqual(error.exception.required_range_km, expected, places=6)
        gap = error.exception.gaps[0]
        self.assertEqual((gap.origin.iata_code, gap.destination.iata_code), ("A", "G"))

    def test_all_failing_segments_are_reported(self):
        index = make_index({"A": (0, 0), "B": (0, 20), "C": (0, 25), "D": (0, 60)})
        with self.assertRaises(RouteUnreachableError) as error:
            plan_route(["A", "B", "C", "D"], FlightProfile(1000, 800, 1000), index=index)
        gaps = [(gap.origin.iata_code, gap.destination.iata_code) for gap in error.exception.gaps]
        self.assertEqual(gaps, [("A", "B"), ("C", "D")])
        self.assertAlmostEqual(error.exception.required_range_km, haversine_km(0, 25, 0, 60), places=6)


def reference_cost(index, start, goal, profile, criterion):
    """Эталон: обычная Дейкстра по явно построенному полному графу."""
    per_km, per_leg = profile.weights(criterion)
    best = {start: 0.0}
    queue = [(0.0, start)]
    while queue:
        cost, node = heapq.heappop(queue)
        if node == goal:
            return cost
        if cost > best[node]:
            continue
        for other in range(len(index)):
            distance = index.distance_km(node, other)
            if other == node or distance > profile.range_km:
                continue
            candidate = cost + per_km * distance + per_leg
            if candidate < best.get(other, float("inf")):
                best[other] = candidate
                heapq.heappush(queue, (candidate, other))
    return None


def reference_bottleneck(index, start, goal):
    """Эталон минимаксного пути: максимальное ребро на пути в минимальном остовном дереве (Прим)."""
    n = len(index)
    in_tree, key, parent = [False] * n, [float("inf")] * n, [None] * n
    key[start] = 0.0
    for _ in range(n):
        node = min((k, i) for i, k in enumerate(key) if not in_tree[i])[1]
        in_tree[node] = True
        for other in range(n):
            if not in_tree[other] and index.distance_km(node, other) < key[other]:
                key[other], parent[other] = index.distance_km(node, other), node
    worst, node = 0.0, goal
    while node != start:
        worst = max(worst, index.distance_km(node, parent[node]))
        node = parent[node]
    return worst


class AgainstReferenceTests(SimpleTestCase):
    """A* с эвристикой обязан давать ту же стоимость, что и полный перебор Дейкстрой."""

    def test_random_instances(self):
        rng = random.Random(42)
        for instance in range(12):
            points = {f"P{i:02d}": (rng.uniform(-60, 70), rng.uniform(-180, 180)) for i in range(45)}
            index = make_index(points)
            profile = FlightProfile(rng.uniform(1500, 6000), rng.uniform(400, 1000), 1000)
            for _ in range(4):
                start, goal = rng.sample(range(len(index)), 2)
                for criterion in Criterion:
                    with self.subTest(instance=instance, start=start, goal=goal, criterion=criterion):
                        per_km, per_leg = profile.weights(criterion)
                        path = find_path(index, start, goal, profile, criterion)
                        expected = reference_cost(index, start, goal, profile, criterion)
                        if expected is None:
                            self.assertIsNone(path)
                            continue
                        legs = [index.distance_km(a, b) for a, b in pairwise(path)]
                        self.assertTrue(all(leg <= profile.range_km for leg in legs))
                        self.assertAlmostEqual(per_km * sum(legs) + per_leg * len(legs), expected, places=6)
                self.assertAlmostEqual(
                    required_range_km(index, start, goal), reference_bottleneck(index, start, goal), places=6
                )


class AirportIndexCacheTests(TestCase):
    def setUp(self):
        self.svo = Airport.objects.create(
            iata_code="SVO", name="Sheremetyevo", country="RU", latitude=55.97, longitude=37.41
        )
        Airport.objects.create(iata_code="LED", name="Pulkovo", country="RU", latitude=59.8, longitude=30.26)
        Airport.objects.create(iata_code="AER", name="Sochi", country="RU", latitude=43.45, longitude=39.95)

    def test_cached_until_table_changes(self):
        first = AirportIndex.current()
        self.assertIs(AirportIndex.current(), first)
        self.assertEqual(len(first), 3)

        self.svo.latitude = 56.0
        self.svo.save()
        updated = AirportIndex.current()
        self.assertIsNot(updated, first)
        self.assertEqual(updated.lat[updated.position("SVO")], 56.0)

        Airport.objects.filter(iata_code="AER").delete()
        self.assertEqual(len(AirportIndex.current()), 2)

    def test_nearest(self):
        nearest = AirportIndex.current().nearest("SVO", limit=5)
        self.assertEqual([ref.iata_code for ref, _ in nearest], ["LED", "AER"])
        self.assertLess(nearest[0][1], nearest[1][1])
