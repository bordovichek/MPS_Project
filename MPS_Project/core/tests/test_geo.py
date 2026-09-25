from itertools import pairwise
from math import pi

import numpy as np
from django.test import SimpleTestCase

from core.geo import EARTH_RADIUS_KM, great_circle_path, haversine_km, haversine_many_km

SVO = (55.9726, 37.4146)
JFK = (40.6398, -73.7789)


class HaversineTests(SimpleTestCase):
    def test_known_distance(self):
        self.assertAlmostEqual(haversine_km(*SVO, *JFK), 7481, delta=15)

    def test_zero_and_symmetry(self):
        self.assertEqual(haversine_km(*SVO, *SVO), 0)
        self.assertAlmostEqual(haversine_km(*SVO, *JFK), haversine_km(*JFK, *SVO), places=9)

    def test_antipodes_are_half_circumference(self):
        self.assertAlmostEqual(haversine_km(10, 20, -10, -160), pi * EARTH_RADIUS_KM, delta=0.001)

    def test_vectorised_version_matches_scalar(self):
        lats = np.array([SVO[0], JFK[0], -33.9, 0.0])
        lons = np.array([SVO[1], JFK[1], 18.6, 179.9])
        expected = [haversine_km(*SVO, lat, lon) for lat, lon in zip(lats, lons, strict=True)]
        lat_rad, lon_rad = np.radians(lats), np.radians(lons)
        actual = haversine_many_km(np.radians(SVO[0]), np.radians(SVO[1]), lat_rad, lon_rad, np.cos(lat_rad))
        np.testing.assert_allclose(actual, expected, rtol=1e-12, atol=1e-9)


class GreatCirclePathTests(SimpleTestCase):
    def test_endpoints_and_density(self):
        path = great_circle_path(*SVO, *JFK, step_km=100)
        self.assertEqual(path[0], (round(SVO[0], 4), round(SVO[1], 4)))
        self.assertEqual(path[-1], (round(JFK[0], 4), round(JFK[1], 4)))
        self.assertEqual(len(path), 76)

    def test_points_lie_on_the_shortest_arc(self):
        path = great_circle_path(*SVO, *JFK, step_km=250)
        travelled = sum(haversine_km(*a, *b) for a, b in pairwise(path))
        self.assertAlmostEqual(travelled, haversine_km(*SVO, *JFK), delta=1)
        self.assertGreater(max(lat for lat, _ in path), SVO[0])

    def test_crossing_antimeridian_keeps_valid_longitudes(self):
        path = great_circle_path(60, 170, 60, -170)
        self.assertTrue(all(-180 <= lon <= 180 for _, lon in path))
        self.assertLess(len(path), 15)

    def test_degenerate_cases(self):
        self.assertEqual(len(great_circle_path(*SVO, *SVO)), 2)
        antipodal = great_circle_path(0, 0, 0, 180)
        self.assertTrue(all(np.isfinite(point).all() for point in antipodal))
        middle = len(antipodal) // 2
        expected = pi * EARTH_RADIUS_KM * middle / (len(antipodal) - 1)
        self.assertAlmostEqual(haversine_km(*antipodal[middle], 0, 0), expected, delta=1)
