"""Поиск маршрута для самолёта с ограниченной дальностью полёта.

Граф неявный и полный: вершины — аэропорты, ребро между двумя аэропортами существует, если
расстояние по дуге большого круга не больше дальности самолёта. Матрицу N×N не строим:
соседей вершины A* считает векторно (numpy) в момент раскрытия этой вершины.
"""

import threading
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from itertools import pairwise
from typing import ClassVar, Self

import numpy as np
from django.conf import settings
from django.db import models

from core.geo import great_circle_path, haversine_km, haversine_many_km
from core.models import Airplane, Airport

LEG_OVERHEAD_H = 0.5
"""Руление, взлёт, набор высоты, снижение и заход на посадку — прибавка к каждому перелёту."""

TURNAROUND_H = 1.0
"""Стоянка на каждой промежуточной посадке: дозаправка и обслуживание."""

MAX_WAYPOINTS = 8
_LEGS_EPS = 1e-9


class Criterion(models.TextChoices):
    TIME = "time", "Быстрее"
    DISTANCE = "distance", "Короче"
    STOPS = "stops", "Меньше посадок"


@dataclass(frozen=True, slots=True)
class FlightProfile:
    range_km: float
    speed_kmh: float
    fuel_burn_kg_h: float

    @classmethod
    def of(cls, airplane: Airplane) -> Self:
        return cls(airplane.max_distance, airplane.cruise_speed, airplane.consumption)

    def flight_time_h(self, distance_km: float) -> float:
        return distance_km / self.speed_kmh + LEG_OVERHEAD_H

    def weights(self, criterion: Criterion) -> tuple[float, float]:
        """Стоимость ребра = per_km * расстояние + per_leg: так все три критерия решает один A*."""
        match criterion:
            case Criterion.TIME:
                return 1 / self.speed_kmh, LEG_OVERHEAD_H + TURNAROUND_H
            case Criterion.DISTANCE:
                return 1.0, 1e-6
            case Criterion.STOPS:
                return 1e-6, 1.0
        raise ValueError(criterion)


@dataclass(frozen=True, slots=True)
class AirportRef:
    iata_code: str
    name: str
    country: str
    latitude: float
    longitude: float


class AirportIndex:
    """Неизменяемый снимок таблицы аэропортов в numpy-массивах для векторных расчётов."""

    _cache: ClassVar[tuple[object, "AirportIndex"] | None] = None
    _lock: ClassVar[threading.Lock] = threading.Lock()

    def __init__(self, rows: Iterable[tuple[str, str, str, float, float]]):
        rows = list(rows)
        self.codes = tuple(row[0] for row in rows)
        self.names = tuple(row[1] for row in rows)
        self.countries = tuple(str(row[2]) for row in rows)
        self.lat = self._frozen([row[3] for row in rows])
        self.lon = self._frozen([row[4] for row in rows])
        self._lat_rad = self._frozen(np.radians(self.lat))
        self._lon_rad = self._frozen(np.radians(self.lon))
        self._cos_lat = self._frozen(np.cos(self._lat_rad))
        self._positions = {code: i for i, code in enumerate(self.codes)}

    @staticmethod
    def _frozen(values) -> np.ndarray:
        array = np.array(values, dtype=float)
        array.flags.writeable = False
        return array

    @classmethod
    def from_db(cls) -> Self:
        rows = Airport.objects.order_by("iata_code").values_list(
            "iata_code", "name", "country", "latitude", "longitude"
        )
        return cls(rows)

    @classmethod
    def current(cls) -> "AirportIndex":
        """Кэш на процесс; пересобирается, когда меняется отпечаток таблицы (число строк + время правки)."""
        stamp = Airport.objects.aggregate(count=models.Count("pk"), updated=models.Max("updated_at"))
        key = (stamp["count"], stamp["updated"])
        with cls._lock:
            if cls._cache is None or cls._cache[0] != key:
                cls._cache = (key, cls.from_db())
            return cls._cache[1]

    def __len__(self) -> int:
        return len(self.codes)

    def __contains__(self, code: str) -> bool:
        return code in self._positions

    def position(self, code: str) -> int:
        return self._positions[code]

    def airport(self, i: int) -> AirportRef:
        return AirportRef(self.codes[i], self.names[i], self.countries[i], float(self.lat[i]), float(self.lon[i]))

    def distance_km(self, i: int, j: int) -> float:
        return haversine_km(self.lat[i], self.lon[i], self.lat[j], self.lon[j])

    def distances_from(self, i: int) -> np.ndarray:
        return haversine_many_km(self._lat_rad[i], self._lon_rad[i], self._lat_rad, self._lon_rad, self._cos_lat)

    def nearest(self, code: str, limit: int = 6) -> list[tuple[AirportRef, float]]:
        i = self.position(code)
        distances = self.distances_from(i)
        order = np.argsort(distances)
        return [(self.airport(j), float(distances[j])) for j in order[: limit + 1] if j != i][:limit]


def find_path(
    index: AirportIndex, start: int, goal: int, profile: FlightProfile, criterion: Criterion
) -> list[int] | None:
    """A* по неявному полному графу. Эвристика допустима и монотонна:
    до цели осталось не меньше расстояния по дуге и не меньше ceil(расстояние / дальность) перелётов.
    Открытое множество — массив f-оценок, поэтому шаг стоит O(N) и выполняется в numpy."""
    per_km, per_leg = profile.weights(criterion)
    to_goal = index.distances_from(goal)
    heuristic = per_km * to_goal + per_leg * np.ceil(to_goal / profile.range_km - _LEGS_EPS)

    g = np.full(len(index), np.inf)
    f = np.full(len(index), np.inf)
    parent = np.full(len(index), -1, dtype=np.intp)
    closed = np.zeros(len(index), dtype=bool)
    g[start], f[start] = 0.0, heuristic[start]

    while True:
        node = int(np.argmin(f))
        if f[node] == np.inf:
            return None
        if node == goal:
            break
        closed[node] = True
        f[node] = np.inf

        distances = index.distances_from(node)
        tentative = g[node] + per_km * distances + per_leg
        better = (distances <= profile.range_km) & ~closed & (tentative < g)
        g[better] = tentative[better]
        f[better] = tentative[better] + heuristic[better]
        parent[better] = node

    path = [goal]
    while path[-1] != start:
        path.append(int(parent[path[-1]]))
    return path[::-1]


def required_range_km(index: AirportIndex, start: int, goal: int) -> float:
    """Минимальная дальность, при которой маршрут существует: минимум по путям от максимального перелёта.
    Та же схема Дейкстры, только вместо суммы — максимум (задача о «узком месте»)."""
    best = np.full(len(index), np.inf)
    key = np.full(len(index), np.inf)
    done = np.zeros(len(index), dtype=bool)
    best[start] = key[start] = 0.0

    while True:
        node = int(np.argmin(key))
        if node == goal:
            return float(best[goal])
        done[node] = True
        key[node] = np.inf

        candidate = np.maximum(best[node], index.distances_from(node))
        better = ~done & (candidate < best)
        best[better] = key[better] = candidate[better]


class RoutingError(Exception):
    pass


class InvalidRouteError(RoutingError):
    pass


class UnknownAirportsError(RoutingError):
    def __init__(self, codes: Sequence[str]):
        self.codes = list(codes)
        super().__init__(f"Аэропорты не найдены: {', '.join(self.codes)}.")


@dataclass(frozen=True, slots=True)
class Gap:
    origin: AirportRef
    destination: AirportRef
    required_range_km: float


class RouteUnreachableError(RoutingError):
    def __init__(self, gaps: Sequence[Gap]):
        self.gaps = list(gaps)
        self.required_range_km = max(gap.required_range_km for gap in self.gaps)
        super().__init__("Самолёт не может пройти маршрут даже с промежуточными посадками.")


@dataclass(frozen=True, slots=True)
class RouteStop:
    airport: AirportRef
    is_waypoint: bool


@dataclass(frozen=True, slots=True)
class Leg:
    origin: AirportRef
    destination: AirportRef
    distance_km: float
    flight_time_h: float | None
    fuel_kg: float | None

    def path(self, step_km: float = 100.0) -> list[tuple[float, float]]:
        o, d = self.origin, self.destination
        return great_circle_path(o.latitude, o.longitude, d.latitude, d.longitude, step_km)


@dataclass(frozen=True, slots=True)
class RoutePlan:
    criterion: Criterion
    profile: FlightProfile | None
    stops: tuple[RouteStop, ...]
    legs: tuple[Leg, ...]

    @property
    def distance_km(self) -> float:
        return sum(leg.distance_km for leg in self.legs)

    @property
    def max_leg_km(self) -> float:
        return max(leg.distance_km for leg in self.legs)

    @property
    def technical_stops(self) -> int:
        return sum(not stop.is_waypoint for stop in self.stops)

    @property
    def flight_time_h(self) -> float | None:
        return sum(leg.flight_time_h for leg in self.legs) if self.profile else None

    @property
    def ground_time_h(self) -> float | None:
        return (len(self.legs) - 1) * TURNAROUND_H if self.profile else None

    @property
    def total_time_h(self) -> float | None:
        return self.flight_time_h + self.ground_time_h if self.profile else None

    @property
    def fuel_kg(self) -> float | None:
        return sum(leg.fuel_kg for leg in self.legs) if self.profile else None

    @property
    def fuel_cost_usd(self) -> float | None:
        return self.fuel_kg * settings.JET_FUEL_PRICE_USD_PER_KG if self.profile else None


def plan_route(
    codes: Sequence[str],
    profile: FlightProfile | None = None,
    criterion: Criterion = Criterion.TIME,
    index: AirportIndex | None = None,
) -> RoutePlan:
    """Маршрут через заданные аэропорты. Без самолёта — прямые перелёты между ними."""
    if not 2 <= len(codes) <= MAX_WAYPOINTS:
        raise InvalidRouteError(f"В маршруте должно быть от 2 до {MAX_WAYPOINTS} аэропортов.")
    if any(a == b for a, b in pairwise(codes)):
        raise InvalidRouteError("Соседние точки маршрута не должны совпадать.")

    criterion = Criterion(criterion)
    index = index or AirportIndex.current()
    if unknown := [code for code in codes if code not in index]:
        raise UnknownAirportsError(unknown)
    if profile is None:
        criterion = Criterion.DISTANCE

    waypoints = [index.position(code) for code in codes]
    sequence, waypoint_positions, gaps = [waypoints[0]], {0}, []
    for start, goal in pairwise(waypoints):
        path = [start, goal] if profile is None else find_path(index, start, goal, profile, criterion)
        if path is None:
            gaps.append(Gap(index.airport(start), index.airport(goal), required_range_km(index, start, goal)))
            continue
        sequence.extend(path[1:])
        waypoint_positions.add(len(sequence) - 1)
    if gaps:
        raise RouteUnreachableError(gaps)

    stops = tuple(RouteStop(index.airport(i), n in waypoint_positions) for n, i in enumerate(sequence))
    legs = []
    for i, j in pairwise(sequence):
        distance = index.distance_km(i, j)
        flight_time = profile.flight_time_h(distance) if profile else None
        fuel = flight_time * profile.fuel_burn_kg_h if profile else None
        legs.append(Leg(index.airport(i), index.airport(j), distance, flight_time, fuel))
    return RoutePlan(criterion, profile, stops, tuple(legs))
