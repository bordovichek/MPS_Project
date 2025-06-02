from django.test import TestCase
from django.urls import reverse
from core.models_dir import Airport, Airplane

class TestMap(TestCase):
    def setUp(self):
        Airport.objects.create(name="Airport A", iata_code="AAA", latitude=0.0, longitude=0.0)
        Airplane.objects.create(
            name="Test Plane",
            max_distance=200,
            cruise_speed=500,
            consumption=2
        )
    def test_map(self):

        response = self.client.get(reverse('map'))

        self.assertEqual(response.status_code, 200)
        self.assertIn("airports", response.context)
        self.assertIn("aircrafts", response.context)

class TestAirplanes(TestCase):
    def setUp(self):

        self.airplane1 = Airplane.objects.create(
            name="Test Plane1",
            max_distance=200,
            cruise_speed=500,
            consumption=2
        )
        self.airplane2 = Airplane.objects.create(
            name="Test Plane2",
            max_distance=200,
            cruise_speed=500,
            consumption=2
        )
    def test_airplanes_list(self):

        response = self.client.get(reverse('airplane_list'))

        self.assertEqual(response.status_code, 200)
        self.assertIn("airplanes", response.context)

    def test_airplanes_detail(self):

        response = self.client.get(reverse('airplane_detail',args=[self.airplane1.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual("Test Plane1",response.context["airplane"].name)

class TestAirports(TestCase):
    def setUp(self):

        self.airport1 = Airport.objects.create(name="Airport A", iata_code="AAA", latitude=0.0, longitude=0.0)
        self.airport2 = Airport.objects.create(name="Airport B", iata_code="BBB", latitude=0.0, longitude=1.0)

    def test_airports_list(self):

        response = self.client.get(reverse('airport_list'))

        self.assertEqual(response.status_code, 200)
        self.assertIn("airports", response.context)

    def test_airports_detail(self):

        response = self.client.get(reverse('airport_detail',args=[self.airport1.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual("Airport A",response.context["airport"].name)

class TestCompare(TestCase):
    def setUp(self):
        self.airplane1 = Airplane.objects.create(
            name="Test Plane1",
            max_distance=200,
            cruise_speed=500,
            consumption=2
        )
        self.airplane2 = Airplane.objects.create(
            name="Test Plane2",
            max_distance=200,
            cruise_speed=500,
            consumption=2
        )

    def test_compare(self):
        response = self.client.get(reverse('compare_airplanes'))
        self.assertEqual(response.status_code, 200)
# Create your tests here.
