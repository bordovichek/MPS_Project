from core.models import Airplane, Airport

AIRPORTS = (
    ("SVO", "Sheremetyevo", "RU", 55.9726, 37.4146),
    ("LED", "Pulkovo Airport", "RU", 59.8003, 30.2625),
    ("AER", "Sochi", "RU", 43.4499, 39.9566),
    ("CDG", "Paris Charles de Gaulle", "FR", 49.0097, 2.5479),
    ("JFK", "John F Kennedy International Airport", "US", 40.6398, -73.7789),
    ("LAX", "Los Angeles International Airport", "US", 33.9425, -118.4081),
    ("HNL", "Honolulu International Airport", "US", 21.3187, -157.9225),
    ("DXB", "Dubai", "AE", 25.2528, 55.3644),
    ("ADL", "Adelaide", "AU", -34.9450, 138.5306),
)


def create_demo_data() -> dict[str, Airplane]:
    for code, name, country, lat, lon in AIRPORTS:
        Airport.objects.create(iata_code=code, name=name, country=country, latitude=lat, longitude=lon)
    return {
        "a320": Airplane.objects.create(
            name="Airbus A320neo",
            capacity=180,
            consumption=2400,
            cruise_speed=840,
            max_distance=6300,
            engines="2 × CFM LEAP-1A / PW1100G",
            year_of_manufacture=2016,
        ),
        "b777": Airplane.objects.create(
            name="Boeing 777-300ER",
            capacity=396,
            consumption=7500,
            cruise_speed=905,
            max_distance=13650,
        ),
        "atr": Airplane.objects.create(
            name="ATR 72-600",
            capacity=74,
            consumption=700,
            cruise_speed=510,
            max_distance=1500,
        ),
        "concorde": Airplane.objects.create(
            name="Concorde",
            capacity=100,
            consumption=25600,
            cruise_speed=2180,
            max_distance=6667,
            in_service=False,
        ),
    }
