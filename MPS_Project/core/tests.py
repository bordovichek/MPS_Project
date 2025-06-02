from django.test import TestCase
from core.logic import (
    haversine,
    get_points_inbetween,
    dijkstra,
    calculate_best_route_for_plane,
    NoRouteException
)
from core.models_dir import Airport, Airplane


class RouteLogicTestCase(TestCase):
    def setUp(self):
        self.airport1 = Airport.objects.create(name="Airport A", iata_code="AAA", latitude=0.0, longitude=0.0)
        self.airport2 = Airport.objects.create(name="Airport B", iata_code="BBB", latitude=0.0, longitude=1.0)
        self.airport3 = Airport.objects.create(name="Airport C", iata_code="CCC", latitude=0.0, longitude=2.0)

        self.airplane = Airplane.objects.create(
            name="Test Plane",
            max_distance=200,
            cruise_speed=500,
            consumption=2
        )

    def test_dijkstra_simple(self):
        result = dijkstra("AAA", "BBB", max_dist_per_segment=200)
        self.assertIn("routes", result)
        self.assertEqual(result["path_airports"], ["AAA", "BBB"])

    def test_dijkstra_no_route(self):
        with self.assertRaises(NoRouteException):
            dijkstra("AAA", "CCC", max_dist_per_segment=1)

    def test_calculate_best_route_for_plane_success(self):
        route = ["AAA", "BBB", "CCC"]
        result = calculate_best_route_for_plane(route, airplane_id=self.airplane.id)
        self.assertTrue(result["success"])
        self.assertEqual(result["plane"], self.airplane.name)
        self.assertEqual(result["flights"], 2)

    def test_calculate_route_without_plane(self):
        result = calculate_best_route_for_plane(["AAA", "BBB", "CCC"])
        self.assertTrue(result["success"])
        self.assertFalse(result["plane_selected"])
        self.assertGreater(result["flights"], 0)

    def test_calculate_with_missing_plane(self):
        result = calculate_best_route_for_plane(["AAA", "BBB"], airplane_id=9999)
        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "Airplane not found.")


