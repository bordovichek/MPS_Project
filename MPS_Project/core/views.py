import json

from django.http import JsonResponse
from django.shortcuts import redirect, render

from core.logic import calculate_best_route_for_plane
from core.models_dir import Airport, Airplane


def home(request):
    return render(request, "web/home.html")


def custom_404_handler(request, exception):
    return redirect('/')


def calculate_route_view(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            airport_iatas = data.get('airport_iatas')
            airplane_id = data.get('airplane_id')

            if not airport_iatas or len(airport_iatas) < 2:
                return JsonResponse({"success": False, "error": "Please provide at least two airport IATA codes."}, status=400)

            result = calculate_best_route_for_plane(airport_iatas, airplane_id)
            return JsonResponse(result, status=200)

        except json.JSONDecodeError:
            return JsonResponse({"success": False, "error": "Invalid JSON format in request body."}, status=400)
        except Exception as e:
            return JsonResponse({"success": False, "error": f"An unexpected error occurred: {str(e)}"}, status=500)
    else:
        return JsonResponse({"success": False, "error": "Only POST requests are allowed."}, status=405)

def get_initial_data_view(request):
    airports = Airport.objects.all().values('iata_code', 'name', 'latitude', 'longitude', 'country', 'description') # Добавлено 'country', 'description'
    airplanes = Airplane.objects.all().values('id', 'name', 'max_distance', 'cruise_speed', 'consumption', 'in_service') # Добавлено 'max_distance', 'cruise_speed', 'consumption', 'in_service'
    return JsonResponse({
        'airports': list(airports),
        'airplanes': list(airplanes)
    })