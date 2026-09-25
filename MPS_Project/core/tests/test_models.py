from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase

from core.models import Airplane, Airport


class AirportModelTests(TestCase):
    def test_iata_code_is_normalised_on_save(self):
        airport = Airport.objects.create(
            iata_code=" svo ", name="Sheremetyevo", country="RU", latitude=55.9, longitude=37.4
        )
        self.assertEqual(airport.iata_code, "SVO")
        self.assertEqual(str(airport), "Sheremetyevo (SVO)")
        self.assertEqual(airport.get_absolute_url(), "/airports/SVO/")
        self.assertEqual(airport.country.name, "Россия")

    def test_validation(self):
        airport = Airport(iata_code="S1O", name="Broken", country="RU", latitude=95, longitude=37)
        with self.assertRaises(ValidationError) as error:
            airport.full_clean()
        self.assertEqual(set(error.exception.message_dict), {"iata_code", "latitude"})


class AirplaneModelTests(TestCase):
    def test_fuel_per_seat(self):
        airplane = Airplane(name="Test", capacity=200, consumption=2500, cruise_speed=850, max_distance=5000)
        self.assertAlmostEqual(airplane.fuel_per_seat_100km, 2500 / (200 * 850) * 100)
        airplane.capacity = None
        self.assertIsNone(airplane.fuel_per_seat_100km)

    def test_speed_and_range_must_be_positive(self):
        airplane = Airplane(name="Test", consumption=1, cruise_speed=0, max_distance=0)
        with self.assertRaises(ValidationError) as error:
            airplane.full_clean()
        self.assertEqual(set(error.exception.message_dict), {"cruise_speed", "max_distance"})


class FixturesTests(TestCase):
    def test_demo_data_loads(self):
        call_command("loaddata", "airplanes", "airports", verbosity=0)
        self.assertEqual(Airplane.objects.count(), 25)
        self.assertEqual(Airport.objects.count(), 2305)
        self.assertFalse(Airport.objects.filter(description="No description").exists())
        self.assertTrue(Airplane.objects.exclude(engines="").count() == 25)
