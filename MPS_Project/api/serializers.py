import re
from itertools import pairwise

from django_countries import countries
from django_countries.serializers import CountryFieldMixin
from rest_framework import serializers

from core.models import Airplane, Airport
from core.routing import MAX_WAYPOINTS, AirportRef, Criterion, RoutePlan, RouteUnreachableError

IATA_RE = re.compile(r"[A-Z]{3}")


class AirplaneSerializer(serializers.ModelSerializer):
    fuel_per_seat_100km = serializers.SerializerMethodField(help_text="кг топлива на пассажира на 100 км")

    class Meta:
        model = Airplane
        fields = [
            "id",
            "name",
            "year_of_manufacture",
            "capacity",
            "engines",
            "consumption",
            "cruise_speed",
            "max_distance",
            "in_service",
            "description",
            "image",
            "fuel_per_seat_100km",
        ]

    def get_fuel_per_seat_100km(self, airplane: Airplane) -> float | None:
        value = airplane.fuel_per_seat_100km
        return round(value, 2) if value is not None else None


class AirportSerializer(CountryFieldMixin, serializers.ModelSerializer):
    country_name = serializers.CharField(source="country.name", read_only=True)

    class Meta:
        model = Airport
        fields = ["id", "iata_code", "name", "country", "country_name", "latitude", "longitude", "description"]


class RouteQuerySerializer(serializers.Serializer):
    airports = serializers.CharField(help_text="IATA-коды через запятую, например SVO,CDG,JFK")
    airplane = serializers.PrimaryKeyRelatedField(
        queryset=Airplane.objects.all(),
        required=False,
        allow_null=True,
        error_messages={"does_not_exist": "Самолёт с id={pk_value} не найден."},
    )
    criterion = serializers.ChoiceField(choices=Criterion.choices, default=Criterion.TIME)

    def validate_airports(self, value: str) -> list[str]:
        codes = [code.strip().upper() for code in value.split(",") if code.strip()]
        if invalid := [code for code in codes if not IATA_RE.fullmatch(code)]:
            raise serializers.ValidationError(f"Некорректные IATA-коды: {', '.join(invalid)}.")
        if not 2 <= len(codes) <= MAX_WAYPOINTS:
            raise serializers.ValidationError(f"Укажите от 2 до {MAX_WAYPOINTS} аэропортов.")
        if any(a == b for a, b in pairwise(codes)):
            raise serializers.ValidationError("Соседние точки маршрута не должны совпадать.")
        return codes


def airplane_brief(airplane: Airplane | None) -> dict | None:
    if airplane is None:
        return None
    return {
        "id": airplane.pk,
        "name": airplane.name,
        "range_km": airplane.max_distance,
        "cruise_speed_kmh": airplane.cruise_speed,
        "fuel_burn_kg_h": airplane.consumption,
        "in_service": airplane.in_service,
    }


def airport_brief(airport: AirportRef) -> dict:
    return {
        "iata_code": airport.iata_code,
        "name": airport.name,
        "country": airport.country,
        "country_name": countries.name(airport.country),
        "latitude": airport.latitude,
        "longitude": airport.longitude,
    }


def _round(value: float | None, digits: int) -> float | None:
    return round(value, digits) if value is not None else None


def route_payload(plan: RoutePlan, airplane: Airplane | None) -> dict:
    return {
        "criterion": plan.criterion,
        "airplane": airplane_brief(airplane),
        "stops": [{**airport_brief(stop.airport), "is_waypoint": stop.is_waypoint} for stop in plan.stops],
        "legs": [
            {
                "origin": leg.origin.iata_code,
                "destination": leg.destination.iata_code,
                "distance_km": round(leg.distance_km, 1),
                "flight_time_h": _round(leg.flight_time_h, 2),
                "fuel_kg": _round(leg.fuel_kg, 0),
                "path": leg.path(),
            }
            for leg in plan.legs
        ],
        "summary": {
            "distance_km": round(plan.distance_km, 1),
            "flights": len(plan.legs),
            "technical_stops": plan.technical_stops,
            "max_leg_km": round(plan.max_leg_km, 1),
            "flight_time_h": _round(plan.flight_time_h, 2),
            "ground_time_h": _round(plan.ground_time_h, 2),
            "total_time_h": _round(plan.total_time_h, 2),
            "fuel_kg": _round(plan.fuel_kg, 0),
            "fuel_cost_usd": _round(plan.fuel_cost_usd, 0),
        },
    }


def _thousands(value: int) -> str:
    return f"{value:,}".replace(",", " ")


def unreachable_payload(error: RouteUnreachableError, airplane: Airplane, suitable: list[Airplane]) -> dict:
    required = round(error.required_range_km)
    worst = max(error.gaps, key=lambda gap: gap.required_range_km)
    return {
        "code": "unreachable",
        "detail": (
            f"{airplane.name} (дальность {_thousands(airplane.max_distance)} км) не долетит "
            f"из {worst.origin.iata_code} в {worst.destination.iata_code} даже с дозаправками: "
            f"нужна дальность не меньше {_thousands(required)} км."
        ),
        "required_range_km": required,
        "gaps": [
            {
                "origin": gap.origin.iata_code,
                "destination": gap.destination.iata_code,
                "required_range_km": round(gap.required_range_km),
            }
            for gap in error.gaps
        ],
        "suitable_airplanes": [airplane_brief(plane) for plane in suitable],
    }
