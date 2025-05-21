from math import cos
from math import sin
import math
import json

from core.models_dir import Airplane
from models_dir.Airport import get_all_airports
import heapq

EARTH_RAD = 6378
KEROSINE_PRICE = 0.698


class NoRouteException(Exception):
    def __init__(self):
        super().__init__("No Route")


class PlaneCantMakeItException(Exception):
    def __init__(self):
        super().__init__("Plane can't make it")


def convert_from_coord_str_to_degrees(coord):
    """Чтоб долго не думать как записи типа 12°34'56" N переводить в float вид"""
    minus = False
    coord = coord.lower()
    res = 0
    if coord.count("w") or coord.count("s"):
        minus = True
    coord = coord.replace("w", "").replace("e", "").replace("n", "").replace("s", "")
    coord = coord.replace("''", "″").replace("'", "′").replace(" ", "").replace("°", ";").replace("′", ";").replace("″",
                                                                                                                    ";").split(
        ";")
    for i in range(min(3, len(coord))):
        res += float(coord[i]) / (60 ** i)
    if minus:
        return -1 * res
    return res


def haversine(lat1, long1, lat2, long2):
    """Это чтоб считать расстояние между 2 точками на шаре"""
    lat1 = math.radians(lat1)
    long1 = math.radians(long1)
    lat2 = math.radians(lat2)
    long2 = math.radians(long2)
    dlat = lat2 - lat1
    dlong = long2 - long1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlong / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))
    return c * EARTH_RAD


def get_best_route_with_plane(route, plane_id):
    """в route нужны iata коды"""
    res = []
    plane_cant = False
    plane = Airplane.objects.filter(id=plane_id).first()
    md = plane.max_distance
    i = 0
    while i < len(route) - 1:

        try:
            res.append(json.loads(dijkstra(route[i], route[i + 1], md)))
            i += 1

        except Exception as e:
            print(i)
            if isinstance(e, PlaneCantMakeItException):
                md = 7000 if md < 7000 else md * 2
                plane_cant = True
            elif isinstance(e, NoRouteException):

                i += 1

    max_dist = 0
    whole_dist = 0
    flights = 0
    for i in res:
        flights += len(i["routes"])
        max_dist = max(i["max_distance"], max_dist)
        whole_dist += i["whole_distance"]
    if not (plane_cant):
        time = whole_dist / float(plane.cruise_speed)
        cost = float(plane.consumption) * time * KEROSINE_PRICE
        d = {"plane": plane.name,
             "plane_selected": True,
             "plane_cant": False,
             "cost": cost,
             "flights": flights,
             "whole_distance": whole_dist,
             "time": time,
             "max_distance": max_dist,
             "route": res
             }
    else:
        d = {"plane": plane.name,
             "plane_selected": True,
             "plane_cant": True,
             "flights": flights,
             "whole_distance": whole_dist,
             "max_distance": max_dist,
             "route": res
             }
    return json.dumps(d)


def get_best_route_without_plane(route):
    """в route нужны iata коды"""
    res = []
    md = 7000
    i = 0
    while i < len(route) - 1:

        try:
            res.append(json.loads(dijkstra(route[i], route[i + 1], md)))
            i += 1
        except PlaneCantMakeItException:
            md *= 2

    max_dist = 0
    whole_dist = 0
    flights = 0
    for i in res:
        flights += len(i["routes"])
        max_dist = max(i["max_distance"], max_dist)
        whole_dist += i["whole_distance"]

    d = {
        "plane_selected": False,
        "flights": flights,
        "whole_distance": whole_dist,
        "max_distance": max_dist,
        "route": res
    }
    return json.dumps(d)


def dijkstra(start, end, max_dist):
    airs = get_all_airports()
    airports_by_code = {a.iata_code: a for a in airs}
    graph = {i.iata_code: {} for i in airs}
    for i in airs:
        for j in airs:
            if i == j:
                continue
            dist = haversine(i.latitude, i.longitude, j.latitude, j.longitude)
            if dist <= max_dist:
                graph[i.iata_code][j.iata_code] = dist
    dist = {i.iata_code: float(10 ** 20) for i in airs}
    prev = {i.iata_code: None for i in airs}
    dist[start] = 0
    queue = [(0, start)]
    while queue:
        cur_dist, cur_air = heapq.heappop(queue)

        if cur_air == end:
            break
        for neighbor in graph[cur_air]:
            weight = graph[cur_air][neighbor]
            new_dist = cur_dist + weight

            if new_dist < dist[neighbor]:
                dist[neighbor] = new_dist
                prev[neighbor] = cur_air
                heapq.heappush(queue, (new_dist, neighbor))

    t = end

    routes = []
    whole_dist = 0
    max_dist = 0

    while prev[t]:
        a1 = airports_by_code[prev[t]]
        a2 = airports_by_code[t]
        routes.append({"start": a1.iata_code,
                       "start_lat": a1.latitide,
                       "start_long": a1.longitude,
                       "dest": a2.iata_code,
                       "dest_lat": a2.latitide,
                       "dest_long": a2.longitude,
                       "dist": graph[prev[t]][t],
                       "inbetween": get_points_inbetween(a1.latitide, a1.longitude, a2.latitide, a2.longitude,
                                                         graph[prev[t]][t])})
        whole_dist += graph[prev[t]][t]
        max_dist = max(graph[prev[t]][t], max_dist)
        t = prev[t]
    routes.reverse()

    js = {"routes": [], "max_distance": max_dist, "whole_distance": whole_dist}
    for i in routes:
        js["routes"].append({f"{i['start']}-{i['dest']}": i})
    return json.dumps(js)


def get_points_inbetween(lat1, long1, lat2, long2, dist):
    res = []
    N = math.ceil(dist / 50)
    lat1 = math.radians(lat1)
    long1 = math.radians(long1)
    lat2 = math.radians(lat2)
    long2 = math.radians(long2)

    p1 = [cos(lat1) * cos(long1), cos(lat1) * sin(long1), sin(lat1)]
    p2 = [cos(lat2) * cos(long2), cos(lat2) * sin(long2), sin(lat2)]

    s = 0
    for i in range(3):
        s += p1[i] * p2[i]
    d = math.acos(s)

    for i in range(N + 1):
        t = float(i) / float(N)
        a = sin((1 - t) * d) / sin(d)
        b = sin(t * d) / sin(d)
        pt = []
        for j in range(3):
            pt.append(a * p1[j] + b * p2[j])

        lat = math.atan2(pt[2], math.sqrt(pt[0] ** 2 + pt[1] ** 2)) * 180 / math.pi
        long = math.atan2(pt[1], pt[0]) * 180 / math.pi
        res.append((lat, long))

    return res
