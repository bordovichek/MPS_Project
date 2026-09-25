"""Геодезия на сфере: расстояния по дуге большого круга и точки для отрисовки дуги."""

from math import asin, ceil, cos, radians, sin, sqrt

import numpy as np

EARTH_RADIUS_KM = 6371.0088


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1, phi2 = radians(lat1), radians(lat2)
    dphi, dlambda = phi2 - phi1, radians(lon2 - lon1)
    a = sin(dphi / 2) ** 2 + cos(phi1) * cos(phi2) * sin(dlambda / 2) ** 2
    return 2 * EARTH_RADIUS_KM * asin(min(1.0, sqrt(a)))


def haversine_many_km(
    lat_rad: float, lon_rad: float, lats_rad: np.ndarray, lons_rad: np.ndarray, cos_lats: np.ndarray
) -> np.ndarray:
    """Расстояния от одной точки до массива точек (углы в радианах, cos широт посчитан заранее)."""
    a = np.sin((lats_rad - lat_rad) / 2) ** 2 + cos(lat_rad) * cos_lats * np.sin((lons_rad - lon_rad) / 2) ** 2
    return 2 * EARTH_RADIUS_KM * np.arcsin(np.sqrt(np.clip(a, 0.0, 1.0)))


def _unit_vector(lat: float, lon: float) -> np.ndarray:
    phi, lam = radians(lat), radians(lon)
    return np.array([cos(phi) * cos(lam), cos(phi) * sin(lam), sin(phi)])


def great_circle_path(
    lat1: float, lon1: float, lat2: float, lon2: float, step_km: float = 100.0
) -> list[tuple[float, float]]:
    """Точки дуги большого круга с шагом ~step_km: сферическая линейная интерполяция (slerp)."""
    p, q = _unit_vector(lat1, lon1), _unit_vector(lat2, lon2)
    omega = float(np.arccos(np.clip(p @ q, -1.0, 1.0)))
    segments = max(1, ceil(omega * EARTH_RADIUS_KM / step_km))
    t = np.linspace(0.0, 1.0, segments + 1)[:, None]

    if omega < 1e-9:
        points = np.repeat(p[None, :], len(t), axis=0)
    elif np.pi - omega < 1e-9:
        # Для диаметрально противоположных точек подходит любая дуга — идём через ортогональную ось.
        axis = np.cross(p, [0.0, 0.0, 1.0] if abs(p[2]) < 0.9 else [1.0, 0.0, 0.0])
        axis /= np.linalg.norm(axis)
        points = np.cos(np.pi * t) * p + np.sin(np.pi * t) * axis
    else:
        points = (np.sin((1 - t) * omega) * p + np.sin(t * omega) * q) / np.sin(omega)

    lats = np.degrees(np.arctan2(points[:, 2], np.hypot(points[:, 0], points[:, 1])))
    lons = np.degrees(np.arctan2(points[:, 1], points[:, 0]))
    path = [(round(float(la), 4), round(float(lo), 4)) for la, lo in zip(lats, lons, strict=True)]
    path[0], path[-1] = (round(lat1, 4), round(lon1, 4)), (round(lat2, 4), round(lon2, 4))
    return path
