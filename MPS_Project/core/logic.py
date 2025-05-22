from math import cos, sin, acos, atan2, degrees, radians, sqrt, ceil, asin
import heapq

# Глобальные константы
EARTH_RAD = 6378
KEROSINE_PRICE = 0.698


class NoRouteException(Exception):
    def __init__(self):
        super().__init__("No Route")


class PlaneCantMakeItException(Exception):
    def __init__(self):
        super().__init__("Plane can't make it")


# Функция convert_from_coord_str_to_degrees, если используется, оставить без изменений
# Если данные в базе уже в float, то эта функция не нужна
def convert_from_coord_str_to_degrees(coord):
    """Чтоб долго не думать как записи типа 12°34'56" N переводить в float вид"""
    minus = False
    coord = coord.lower()
    res = 0
    if coord.count("w") or coord.count("s"):
        minus = True
    coord = coord.replace("w", "").replace("e", "").replace("n", "").replace("s", "")
    coord = coord.replace("''", "″").replace("'", "′").replace(" ", "").replace("°", ";").replace("′", ";").replace(
        "″", ";").split(
        ";")
    for i in range(min(3, len(coord))):
        res += float(coord[i]) / (60 ** i)
    if minus:
        return -1 * res
    return res


def haversine(lat1, long1, lat2, long2):
    """Это чтоб считать расстояние между 2 точками на шаре"""
    lat1 = radians(lat1)
    long1 = radians(long1)
    lat2 = radians(lat2)
    long2 = radians(long2)
    dlat = lat2 - lat1
    dlong = long2 - long1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlong / 2) ** 2
    c = 2 * asin(sqrt(a))
    return c * EARTH_RAD


def get_points_inbetween(lat1, long1, lat2, long2, dist):
    res = []
    N = max(2, ceil(dist / 50)) # Минимум 2 точки (начало и конец)
    lat1 = radians(lat1)
    long1 = radians(long1)
    lat2 = radians(lat2)
    long2 = radians(long2)

    p1 = [cos(lat1) * cos(long1), cos(lat1) * sin(long1), sin(lat1)]
    p2 = [cos(lat2) * cos(long2), cos(lat2) * sin(long2), sin(lat2)]

    s = sum(x * y for x, y in zip(p1, p2))
    d = acos(max(-1.0, min(1.0, s))) # Clamp s to [-1, 1] to prevent math domain errors

    for i in range(N + 1):
        t = float(i) / float(N)
        if d == 0: # Handle the case where the points are the same
            a = 1 - t
            b = t
        else:
            a = sin((1 - t) * d) / sin(d)
            b = sin(t * d) / sin(d)
        pt = [a * p1[j] + b * p2[j] for j in range(3)]

        lat = degrees(atan2(pt[2], sqrt(pt[0] ** 2 + pt[1] ** 2)))
        long = degrees(atan2(pt[1], pt[0]))
        res.append([lat, long]) # Возвращаем список, а не кортеж
    return res


def dijkstra(start_iata, end_iata, max_dist, airports_data_map):
    """
    Реализует алгоритм Дейкстры для поиска кратчайшего пути между двумя аэропортами.
    Принимает airports_data_map как словарь {iata_code: {latitude, longitude, name, ...}}.
    Возвращает словарь с информацией о маршруте или None, если маршрут не найден.
    """
    graph = {code: {} for code in airports_data_map.keys()}

    # Построение графа: добавляем ребра только если расстояние <= max_dist
    for i_code, air1 in airports_data_map.items():
        for j_code, air2 in airports_data_map.items():
            if i_code == j_code:
                continue

            dist = haversine(air1['latitude'], air1['longitude'], air2['latitude'], air2['longitude'])
            if dist <= max_dist:
                graph[i_code][j_code] = dist

    dist = {code: float('inf') for code in airports_data_map.keys()}
    prev = {code: None for code in airports_data_map.keys()}
    priority_queue = [(0, start_iata)] # (расстояние, IATA-код)

    dist[start_iata] = 0

    while priority_queue:
        current_dist, current_iata = heapq.heappop(priority_queue)

        if current_dist > dist[current_iata]:
            continue

        if current_iata == end_iata:
            break

        for neighbor_iata, weight in graph[current_iata].items():
            new_dist = current_dist + weight
            if new_dist < dist[neighbor_iata]:
                dist[neighbor_iata] = new_dist
                prev[neighbor_iata] = current_iata
                heapq.heappush(priority_queue, (new_dist, neighbor_iata))

    # Восстановление пути
    path_airports_iata = []
    routes_segments = []
    whole_distance = 0
    max_segment_distance = 0

    # Если маршрут не найден (конечная точка недостижима)
    if prev[end_iata] is None and end_iata != start_iata:
        # Можно сгенерировать исключение NoRouteException, но для API лучше вернуть None
        return None

    current = end_iata
    while current is not None:
        path_airports_iata.append(current)
        current = prev[current]
    path_airports_iata.reverse() # Получаем путь в правильном порядке (от старта до конца)

    # Если начальная и конечная точка совпадают, путь состоит из одной точки
    if len(path_airports_iata) == 1 and start_iata == end_iata:
        # Специальный случай: маршрут из одной точки
        return {
            'routes': [],
            'max_distance': 0.0,
            'whole_distance': 0.0,
            'path_airports': path_airports_iata
        }
    elif len(path_airports_iata) == 0: # Это не должно произойти, если start_iata != end_iata и маршрут не найден
        return None

    # Формируем сегменты маршрута
    for i in range(len(path_airports_iata) - 1):
        segment_start_iata = path_airports_iata[i]
        segment_end_iata = path_airports_iata[i+1]

        s_airport = airports_data_map[segment_start_iata]
        e_airport = airports_data_map[segment_end_iata]

        segment_dist = graph[segment_start_iata][segment_end_iata] # Берем dist из графа

        routes_segments.append({
            'start': segment_start_iata,
            # 'start_lat': s_airport['latitude'], # Эти поля не нужны на фронте, так как есть inbetween
            # 'start_long': s_airport['longitude'],
            'dest': segment_end_iata,
            # 'dest_lat': e_airport['latitude'],
            # 'dest_long': e_airport['longitude'],
            'dist': segment_dist, # Дистанция сегмента
            'inbetween': get_points_inbetween(s_airport['latitude'], s_airport['longitude'], e_airport['latitude'], e_airport['longitude'], segment_dist)
        })
        whole_distance += segment_dist
        max_segment_distance = max(max_segment_distance, segment_dist)

    return {
        'routes': routes_segments,
        'max_distance': max_segment_distance,
        'whole_distance': whole_distance,
        'path_airports': path_airports_iata # Возвращаем список IATA-кодов всех аэропортов в пути
    }