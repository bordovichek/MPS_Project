from collections.abc import Callable, Sequence
from dataclasses import dataclass
from operator import attrgetter
from typing import Literal

from core.models import Airplane

type Number = int | float


@dataclass(frozen=True, slots=True)
class Metric:
    label: str
    unit: str
    value: Callable[[Airplane], Number | None]
    better: Literal["higher", "lower"] | None = None
    number_format: str = "0g"


@dataclass(frozen=True, slots=True)
class Cell:
    value: Number | None
    share: float
    verdict: Literal["best", "worst", ""]


@dataclass(frozen=True, slots=True)
class Row:
    metric: Metric
    cells: list[Cell]


METRICS = (
    Metric("Максимальная дальность", "км", attrgetter("max_distance"), "higher"),
    Metric("Крейсерская скорость", "км/ч", attrgetter("cruise_speed"), "higher"),
    Metric("Пассажировместимость", "мест", attrgetter("capacity"), "higher"),
    Metric("Расход топлива", "кг/ч", attrgetter("consumption"), "lower"),
    Metric("Расход на пассажира", "кг на 100 км", attrgetter("fuel_per_seat_100km"), "lower", "2g"),
    Metric("Год выпуска", "", attrgetter("year_of_manufacture"), number_format="0"),
)


def build_comparison(airplanes: Sequence[Airplane]) -> list[Row]:
    """Лучшее значение подсвечивается всегда, худшее — только когда сравниваются три самолёта."""
    rows = []
    for metric in METRICS:
        values = [metric.value(airplane) for airplane in airplanes]
        known = [value for value in values if value is not None]
        best = worst = None
        if metric.better and len(set(known)) > 1:
            best, worst = (max(known), min(known)) if metric.better == "higher" else (min(known), max(known))
            if len(airplanes) < 3:
                worst = None
        top = max(known, default=0)
        cells = []
        for value in values:
            verdict = "" if value is None else "best" if value == best else "worst" if value == worst else ""
            share = value / top if metric.better and value and top else 0.0
            cells.append(Cell(value, share, verdict))
        rows.append(Row(metric, cells))
    return rows
