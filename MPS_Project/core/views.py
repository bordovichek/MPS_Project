import json

from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.generic import TemplateView

from core.logic import calculate_best_route_for_plane
from core.models_dir import Airport, Airplane


class Home(TemplateView):
    template_name = 'web/home.html'


def custom_404_handler(request, exception):
    return redirect('/')


def calculate_route_view(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            airport_iatas = data.get('airport_iatas')
            airplane_id = data.get('airplane_id')

            if not airport_iatas or len(airport_iatas) < 2:
                return JsonResponse({"success": False, "error": "Please provide at least two airport IATA codes."},
                                    status=400)

            result = calculate_best_route_for_plane(airport_iatas, airplane_id)
            return JsonResponse(result, status=200)

        except json.JSONDecodeError:
            return JsonResponse({"success": False, "error": "Invalid JSON format in request body."}, status=400)
        except Exception as e:
            return JsonResponse({"success": False, "error": f"An unexpected error occurred: {str(e)}"}, status=500)
    else:
        return JsonResponse({"success": False, "error": f"Only POST requests are allowed. Received: {request.method}"},
                            status=405)


def get_initial_data_view(request):
    airports = Airport.objects.all().values('iata_code', 'name', 'latitude', 'longitude', 'country', 'description')
    airplanes = Airplane.objects.all().values('id', 'name', 'max_distance', 'cruise_speed', 'consumption', 'in_service')
    return JsonResponse({
        'airports': list(airports),
        'airplanes': list(airplanes)
    })


def compare_airplanes_view(request):
    airplane_ids_str = request.GET.get('ids')
    selected_airplanes = []

    attributes_bigger_is_better = [
        'capacity', 'engine_power', 'cruise_speed', 'max_distance'
    ]
    attributes_smaller_is_better = [
        'consumption'
    ]

    if airplane_ids_str:
        airplane_ids = [int(x.strip()) for x in airplane_ids_str.split(',') if x.strip().isdigit()]
        airplane_ids = airplane_ids[:3]

        for airplane_id in airplane_ids:
            try:
                airplane = Airplane.objects.get(pk=airplane_id)
                selected_airplanes.append(airplane)
            except Airplane.DoesNotExist:
                pass

    comparison_data = {}
    if len(selected_airplanes) >= 2:
        all_comparison_attributes = attributes_bigger_is_better + attributes_smaller_is_better

        for attr in all_comparison_attributes:
            values_with_planes = []
            for plane in selected_airplanes:
                val = getattr(plane, attr)
                if val is None:
                    values_with_planes.append({'value': None, 'plane': plane, 'display': "Н/Д"})
                elif isinstance(val, (int, float)):
                    values_with_planes.append({'value': val, 'plane': plane, 'display': val})
                else:
                    values_with_planes.append({'value': None, 'plane': plane, 'display': val})

            numeric_values_for_sort = [item['value'] for item in values_with_planes if item['value'] is not None]

            if len(numeric_values_for_sort) < 2:
                comparison_data[attr] = [{'display': item['display'], 'class': ""} for item in values_with_planes]
                continue

            sorted_unique_values = sorted(list(set(numeric_values_for_sort)))

            min_val = sorted_unique_values[0]
            max_val = sorted_unique_values[-1]

            attr_results = []
            for item in values_with_planes:
                current_value = item['value']
                display_value = item['display']
                highlight_class = ""

                if current_value is not None:
                    if len(selected_airplanes) == 2:
                        if attr in attributes_bigger_is_better:
                            if current_value == max_val:
                                highlight_class = "highlight-mild"
                        elif attr in attributes_smaller_is_better:
                            if current_value == min_val:
                                highlight_class = "highlight-mild"
                    elif len(selected_airplanes) == 3:
                        if attr in attributes_bigger_is_better:
                            if current_value == max_val:
                                highlight_class = "highlight-mild"
                            elif current_value == min_val:
                                highlight_class = "highlight-strong"
                        elif attr in attributes_smaller_is_better:
                            if current_value == min_val:
                                highlight_class = "highlight-mild"
                            elif current_value == max_val:
                                highlight_class = "highlight-strong"

                attr_results.append({
                    'display': display_value,
                    'class': highlight_class
                })
            comparison_data[attr] = attr_results
    else:
        all_comparison_attributes = attributes_bigger_is_better + attributes_smaller_is_better
        for attr in all_comparison_attributes:
            comparison_data[attr] = []
            for plane in selected_airplanes:
                comparison_data[attr].append({
                    'display': getattr(plane, attr) if getattr(plane, attr) is not None else "Н/Д",
                    'class': ""
                })

    return render(request, 'web/compare_airplanes.html', {
        'selected_airplanes': selected_airplanes,
        'comparison_data': comparison_data,
    })
