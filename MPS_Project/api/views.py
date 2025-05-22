import json
import logging

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from rest_framework import generics

from core.logic import dijkstra, haversine, get_points_inbetween, KEROSINE_PRICE
from core.mixins import CaseInsensitiveLookupMixin
from core.models_dir import Airplane, Airport
from .serializers import AirplaneSerializer, AirportSerializer


class AirplaneListView(generics.ListAPIView):
    queryset = Airplane.objects.all()
    serializer_class = AirplaneSerializer


class AirportListView(generics.ListAPIView):
    queryset = Airport.objects.all()
    serializer_class = AirportSerializer


class AirplaneDetailView(CaseInsensitiveLookupMixin, generics.RetrieveAPIView):
    queryset = Airplane.objects.all()
    serializer_class = AirplaneSerializer
    lookup_field = "name"


class AirportDetailView(CaseInsensitiveLookupMixin, generics.RetrieveAPIView):
    queryset = Airport.objects.all()
    serializer_class = AirportSerializer
    lookup_field = "iata_code"


logger = logging.getLogger(__name__)


@csrf_exempt
@require_POST
def calculate_route(request):
    try:
        data = json.loads(request.body)
        print(data)
        selected_airport_iats = data.get('airport_iats', [])
        aircraft_name = data.get('aircraft_name')
        print(selected_airport_iats)

        if not selected_airport_iats or len(selected_airport_iats) < 2:
            return JsonResponse({'error': 'Пожалуйста, выберите как минимум два аэропорта.'}, status=400)

        try:
            aircraft = Airplane.objects.get(name=aircraft_name)
            max_distance = aircraft.max_distance
            cruise_speed = aircraft.cruise_speed
            consumption = aircraft.consumption
        except Airplane.DoesNotExist:
            return JsonResponse({'error': 'Выбранный самолет не найден.'}, status=400)
        except AttributeError:
            return JsonResponse(
                {'error': 'У выбранного самолета отсутствуют необходимые данные (дальность, скорость, расход).'},
                status=400)

        all_airports_data = Airport.objects.all().values('iata_code', 'latitude', 'longitude', 'name', 'country')
        airports_by_code = {a['iata_code']: a for a in all_airports_data}

        total_whole_distance = 0
        total_flights = 0
        overall_max_segment_distance = 0
        all_segments_found = True
        all_path_airports_iata = set()

        final_route_segments_for_frontend = []

        for i in range(len(selected_airport_iats) - 1):
            start_iata = selected_airport_iats[i]
            end_iata = selected_airport_iats[i + 1]

            if start_iata not in airports_by_code or end_iata not in airports_by_code:
                return JsonResponse(
                    {'error': f'Один из выбранных аэропортов ({start_iata} или {end_iata}) не найден в базе данных.'},
                    status=400)

            route_segment_result = dijkstra(
                start_iata,
                end_iata,
                max_distance,
                airports_by_code
            )

            if route_segment_result and route_segment_result['routes'] is not None:
                for segment_data in route_segment_result['routes']:
                    path_coords = []
                    if segment_data['inbetween']:
                        for iata_code in segment_data['inbetween']:
                            if iata_code in airports_by_code:
                                path_coords.append(
                                    [airports_by_code[iata_code]['latitude'], airports_by_code[iata_code]['longitude']])
                    if segment_data['start'] in airports_by_code:
                        path_coords.insert(0, [airports_by_code[segment_data['start']]['latitude'],
                                               airports_by_code[segment_data['start']]['longitude']])
                    if segment_data['dest'] in airports_by_code:
                        path_coords.append([airports_by_code[segment_data['dest']]['latitude'],
                                            airports_by_code[segment_data['dest']]['longitude']])

                    final_route_segments_for_frontend.append({
                        'path': path_coords,
                        'intermediate_airports': segment_data['inbetween']
                    })
                total_whole_distance += route_segment_result['whole_distance']
                total_flights += len(route_segment_result['routes'])
                overall_max_segment_distance = max(overall_max_segment_distance, route_segment_result['max_distance'])

                for iata_code in route_segment_result['path_airports']:
                    all_path_airports_iata.add(iata_code)

            else:
                all_segments_found = False
                start_airport_obj = airports_by_code.get(start_iata)
                end_airport_obj = airports_by_code.get(end_iata)
                if start_airport_obj and end_airport_obj:
                    straight_dist = haversine(start_airport_obj['latitude'], start_airport_obj['longitude'],
                                              end_airport_obj['latitude'], end_airport_obj['longitude'])
                    final_route_segments_for_frontend.append({
                        'path': get_points_inbetween(start_airport_obj['latitude'], start_airport_obj['longitude'],
                                                     end_airport_obj['latitude'], end_airport_obj['longitude'],
                                                     straight_dist),
                        'intermediate_airports': [],
                    })

        estimated_time = 0
        estimated_cost = 0

        if cruise_speed and cruise_speed > 0:
            estimated_time = total_whole_distance / cruise_speed
            if consumption:
                estimated_cost = consumption * estimated_time * KEROSINE_PRICE
        else:
            logger.warning(
                f"Самолет {aircraft_name} имеет нулевую скорость или расход. Время/стоимость не будут рассчитаны.")

        response_data = {
            'plane_name': aircraft_name,  # Используем aircraft_name из полученных данных
            'total_distance': total_whole_distance,  # Имя ключа изменено на total_distance
            'total_flights': total_flights,  # Имя ключа изменено на total_flights
            'max_segment_distance': overall_max_segment_distance,
            'estimated_time': estimated_time,
            'estimated_cost': estimated_cost,
            'routes': final_route_segments_for_frontend,  # Имя ключа изменено на routes
            'intermediate_airports_on_path': list(all_path_airports_iata),  # Новое поле для всех промежуточных IATA
            'selected_airports_on_path': selected_airport_iats,  # Изначально выбранные IATA
        }

        if not all_segments_found:
            return JsonResponse({
                'error': 'Не удалось найти оптимальный маршрут для всех выбранных сегментов. Некоторые участки показаны прямой красной линией (за пределами дальности самолета).',
                'route_data': response_data
            }, status=200)

        return JsonResponse(response_data)  # Возвращаем только route_data, если все хорошо

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Неверный формат запроса. Ожидается JSON.'}, status=400)
    except Exception as e:
        logger.exception("Ошибка при расчете маршрута:")
        return JsonResponse({'error': f'Внутренняя ошибка сервера: {str(e)}'}, status=500)
