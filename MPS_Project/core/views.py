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
        return JsonResponse({"success": False, "error": "Only POST requests are allowed."}, status=405)


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
    comparison_attributes = [
        'capacity', 'engine_power', 'consumption',
        'cruise_speed', 'max_distance'
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
        for attr in comparison_attributes:
            values = [getattr(plane, attr, 0) or 0 for plane in selected_airplanes]
            numeric_values = [v for v in values if v is not None and v != 0]
            comparison_data[attr] = []
            if len(numeric_values) >= 2:
                for i, plane in enumerate(selected_airplanes):
                    current_value = getattr(plane, attr, 0) or 0
                    highlight_class = ""
                    if current_value is not None and current_value != 0:
                        max_diff_percent = 0.0
                        for other_val in numeric_values:
                            if other_val != 0:
                                diff_percent = abs(current_value - other_val) / other_val * 100
                                if diff_percent > max_diff_percent:
                                    max_diff_percent = diff_percent
                        if max_diff_percent > 200:
                            highlight_class = "highlight-strong"
                        elif max_diff_percent >= 51:
                            highlight_class = "highlight-mild"

                    comparison_data[attr].append({
                        'value': current_value if current_value is not None else "Н/Д",
                        'display': getattr(plane, attr) if getattr(plane, attr) is not None else "Н/Д",
                        'class': highlight_class
                    })
            else:
                for plane in selected_airplanes:
                    comparison_data[attr].append({
                        'value': getattr(plane, attr, 0) or 0,
                        'display': getattr(plane, attr) if getattr(plane, attr) is not None else "Н/Д",
                        'class': ""
                    })

    return render(request, 'web/compare_airplanes.html', {
        'selected_airplanes': selected_airplanes,
        'comparison_data': comparison_data,
    })
