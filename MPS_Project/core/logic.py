# --- КОНСТАНТЫ ---
import heapq
from math import radians, sin, cos, sqrt, asin, acos, atan2, ceil, pi

from core.models_dir import Airport, Airplane

EARTH_RAD = 6378
KEROSINE_PRICE = 0.698  # Цена керосина за кг (пример)


# --- ИСКЛЮЧЕНИЯ ---
class NoRouteException(Exception):
    def __init__(self, message="No Route Found"):
        super().__init__(message)


class PlaneCantMakeItException(Exception):
    def __init__(self, message="Plane cannot make this segment even with increased max distance"):
        super().__init__(message)


# --- ГЕОМЕТРИЧЕСКИЕ ФУНКЦИИ (Остаются без изменений) ---
def haversine(lat1, long1, lat2, long2):
    """Это чтоб считать расстояние между 2 точками на шаре"""
    lat1_rad = radians(lat1)
    long1_rad = radians(long1)
    lat2_rad = radians(lat2)
    long2_rad = radians(long2)

    dlat = lat2_rad - lat1_rad
    dlong = long2_rad - long1_rad

    a = sin(dlat / 2) ** 2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlong / 2) ** 2
    c = 2 * asin(sqrt(a))
    return c * EARTH_RAD


def get_points_inbetween(lat1, long1, lat2, long2, dist):
    """
    Рассчитывает промежуточные точки между двумя географическими координатами
    для гладкой отрисовки маршрута.
    """
    res = []
    N = ceil(dist / 50)

    lat1_rad = radians(lat1)
    long1_rad = radians(long1)
    lat2_rad = radians(lat2)
    long2_rad = radians(long2)

    p1 = [cos(lat1_rad) * cos(long1_rad), cos(lat1_rad) * sin(long1_rad), sin(lat1_rad)]
    p2 = [cos(lat2_rad) * cos(long2_rad), cos(lat2_rad) * sin(long2_rad), sin(lat2_rad)]

    s = 0
    for i in range(3):
        s += p1[i] * p2[i]
    d = acos(max(-1.0, min(1.0, s)))  # Убедимся, что acos получает значение в диапазоне [-1, 1]

    for i in range(N + 1):
        t = float(i) / float(N)

        # Обработка случая, когда точки очень близки (d очень мало)
        if d < 1e-6:
            a = 1 - t
            b = t
        else:
            a = sin((1 - t) * d) / sin(d)
            b = sin(t * d) / sin(d)

        pt = []
        for j in range(3):
            pt.append(a * p1[j] + b * p2[j])

        # ВОТ ГЛАВНОЕ ИСПРАВЛЕНИЕ: ИСПОЛЬЗОВАНИЕ math.pi ДЛЯ КОНВЕРСИИ
        lat_deg = atan2(pt[2], sqrt(pt[0] ** 2 + pt[1] ** 2)) * 180 / pi
        long_deg = atan2(pt[1], pt[0]) * 180 / pi
        res.append([lat_deg, long_deg]) # Возвращаем список, как ожидает фронтенд

    return res


# --- ОСНОВНАЯ ЛОГИКА АЛГОРИТМОВ (С ИЗМЕНЕНИЯМИ ДЛЯ Django ORM) ---

def dijkstra(start_iata, end_iata, max_dist_per_segment):
    """
    Находит кратчайший путь между двумя аэропортами с использованием алгоритма Дейкстры.
    Использует Django ORM для получения данных об аэропортах.
    """
    # Получаем все активные аэропорты из базы данных один раз
    all_airports = Airport.objects.filter()
    airports_by_code = {a.iata_code: a for a in all_airports}

    if start_iata not in airports_by_code or end_iata not in airports_by_code:
        raise NoRouteException("Start or end airport IATA code not found in database or not in service.")

    graph = {a.iata_code: {} for a in all_airports}
    for i in all_airports:
        for j in all_airports:
            if i.iata_code == j.iata_code:
                continue
            dist = haversine(i.latitude, i.longitude, j.latitude, j.longitude)
            if dist <= max_dist_per_segment:
                graph[i.iata_code][j.iata_code] = dist

    dist = {a.iata_code: float('inf') for a in all_airports}
    prev = {a.iata_code: None for a in all_airports}

    dist[start_iata] = 0
    queue = [(0, start_iata)]

    while queue:
        cur_dist, cur_air_iata = heapq.heappop(queue)

        if cur_dist > dist[cur_air_iata]:
            continue

        if cur_air_iata == end_iata:
            break

        for neighbor_iata, weight in graph[cur_air_iata].items():
            new_dist = cur_dist + weight

            if new_dist < dist[neighbor_iata]:
                dist[neighbor_iata] = new_dist
                prev[neighbor_iata] = cur_air_iata
                heapq.heappush(queue, (new_dist, neighbor_iata))

    if dist[end_iata] == float('inf'):
        raise NoRouteException(
            f"No route found from {start_iata} to {end_iata} with max segment distance {max_dist_per_segment} km.")

    path_airports_iatas = []
    current = end_iata
    while current is not None:
        path_airports_iatas.append(current)
        current = prev[current]
    path_airports_iatas.reverse()

    routes_details = []
    whole_dist = 0
    max_segment_dist = 0

    for i in range(len(path_airports_iatas) - 1):
        segment_start_iata = path_airports_iatas[i]
        segment_end_iata = path_airports_iatas[i + 1]

        start_airport = airports_by_code[segment_start_iata]
        end_airport = airports_by_code[segment_end_iata]
        segment_dist = graph[segment_start_iata][segment_end_iata]

        routes_details.append({
            "start": start_airport.iata_code,
            "start_lat": start_airport.latitude,
            "start_long": start_airport.longitude,
            "dest": end_airport.iata_code,
            "dest_lat": end_airport.latitude,
            "dest_long": end_airport.longitude,
            "dist": segment_dist,
            "inbetween": get_points_inbetween(
                start_airport.latitude, start_airport.longitude,
                end_airport.latitude, end_airport.longitude, segment_dist
            )
        })
        whole_dist += segment_dist
        max_segment_dist = max(max_segment_dist, segment_dist)

    return {
        "routes": routes_details,
        "max_distance": max_segment_dist,
        "whole_distance": whole_dist,
        "path_airports": path_airports_iatas  # Все IATA-коды аэропортов в этом пути
    }


def calculate_best_route_for_plane(route_iatas: list[str], airplane_id: int = None):
    """
    Рассчитывает лучший маршрут для заданного самолета (или без самолета).
    Объединяет логику get_best_route_with_plane и get_best_route_without_plane.
    Использует Django ORM для получения данных о самолете.
    """

    selected_plane = None
    if airplane_id:
        try:
            # Получаем объект Airplane из базы данных
            selected_plane = Airplane.objects.get(pk=airplane_id)
        except Airplane.DoesNotExist:
            return {
                "success": False,
                "error": "Airplane not found."
            }

    # Если самолет не выбран, или у него нет max_distance, используем дефолт
    initial_max_dist_per_segment = selected_plane.max_distance if selected_plane and selected_plane.max_distance else 7000

    total_whole_distance = 0
    total_flights = 0
    overall_max_segment_distance = 0
    all_segment_results = []

    all_path_airports_set = set()  # Множество для сбора всех уникальных IATA-кодов аэропортов в конечном пути

    plane_cant_make_it = False  # Флаг, если пришлось увеличить дальность полета самолета

    for i in range(len(route_iatas) - 1):
        start_iata = route_iatas[i]
        end_iata = route_iatas[i + 1]

        segment_found = False
        temp_max_dist_for_segment = initial_max_dist_per_segment

        # Пробуем найти маршрут, увеличивая max_dist_per_segment
        for attempt in range(3):  # Максимум 3 попытки, удваивая дальность
            try:
                segment_result = dijkstra(start_iata, end_iata, temp_max_dist_for_segment)
                all_segment_results.append(segment_result)
                total_whole_distance += segment_result["whole_distance"]
                total_flights += len(segment_result["routes"])
                overall_max_segment_distance = max(overall_max_segment_distance, segment_result["max_distance"])

                # Добавляем все аэропорты из этого сегмента в общий набор
                for airport_iata in segment_result["path_airports"]:
                    all_path_airports_set.add(airport_iata)

                segment_found = True
                if temp_max_dist_for_segment > initial_max_dist_per_segment:
                    plane_cant_make_it = True  # Отмечаем, что пришлось увеличивать дальность
                break  # Маршрут для сегмента найден
            except NoRouteException:
                if attempt < 2:
                    temp_max_dist_for_segment *= 2
                    plane_cant_make_it = True  # Отмечаем, что пришлось увеличивать дальность
                else:
                    # Если после всех попыток маршрут не найден, добавляем "прямую" линию и ошибку
                    start_airport = Airport.objects.filter(iata_code=start_iata).first()
                    end_airport = Airport.objects.filter(iata_code=end_iata).first()
                    if start_airport and end_airport:
                        straight_dist = haversine(start_airport.latitude, start_airport.longitude, end_airport.latitude,
                                                  end_airport.longitude)
                        all_segment_results.append({
                            "routes": [{
                                "start": start_iata,
                                "start_lat": start_airport.latitude,
                                "start_long": start_airport.longitude,
                                "dest": end_iata,
                                "dest_lat": end_airport.latitude,
                                "dest_long": end_airport.longitude,
                                "dist": straight_dist,
                                "inbetween": [[start_airport.latitude, start_airport.longitude],
                                              [end_airport.latitude, end_airport.longitude]]
                            }],
                            "max_distance": straight_dist,
                            "whole_distance": straight_dist,
                            "path_airports": [start_iata, end_iata]
                        })
                        total_whole_distance += straight_dist
                        total_flights += 1
                        overall_max_segment_distance = max(overall_max_segment_distance, straight_dist)
                        all_path_airports_set.add(start_iata)
                        all_path_airports_set.add(end_iata)

                    segment_found = False
                    return {
                        "success": False,
                        "error": f"Could not find optimal route for segment {start_iata}-{end_iata}. Marked as direct. This aircraft cannot complete the route even with layovers.",
                        "plane": selected_plane.name if selected_plane else "Not selected",
                        "plane_selected": bool(selected_plane),
                        "plane_cant": True,
                        "flights": total_flights,
                        "whole_distance": round(total_whole_distance, 2),
                        "max_distance": round(overall_max_segment_distance, 2),
                        "route_segments": all_segment_results,
                        "all_path_airports_iatas": list(all_path_airports_set)
                    }

    estimated_time = 0
    estimated_cost = 0
    plane_name = "Not selected"

    if selected_plane:
        plane_name = selected_plane.name
        if selected_plane.cruise_speed and selected_plane.cruise_speed > 0:
            estimated_time = total_whole_distance / selected_plane.cruise_speed
            if selected_plane.consumption:
                estimated_cost = selected_plane.consumption * estimated_time * KEROSINE_PRICE
        else:
            return {
                "success": False,
                "error": "Selected plane has no cruise speed or consumption data for calculation.",
                "plane": plane_name,
                "plane_selected": True,
                "plane_cant": False,
                "cost": 0, "flights": total_flights,
                "whole_distance": round(total_whole_distance, 2),
                "time": 0, "max_distance": round(overall_max_segment_distance, 2),
                "route_segments": all_segment_results,
                "all_path_airports_iatas": list(all_path_airports_set)
            }
    elif total_flights > 0:
        pass
    return {
        "success": True,
        "plane": plane_name,
        "plane_selected": bool(selected_plane),
        "plane_cant": plane_cant_make_it,
        "cost": round(estimated_cost, 2),
        "flights": total_flights,
        "whole_distance": round(total_whole_distance, 2),
        "time": round(estimated_time, 2),
        "max_distance": round(overall_max_segment_distance, 2),
        "route_segments": all_segment_results,
        "all_path_airports_iatas": list(all_path_airports_set)
    }
