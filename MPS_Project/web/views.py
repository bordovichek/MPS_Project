from django.shortcuts import render

from core.models_dir import Airport, Airplane


def flight_view(request):
    airports = Airport.objects.all().order_by("name")
    aircrafts = Airplane.objects.all()
    return render(request, "web/map.html", {
        "airports": airports,
        "aircrafts": aircrafts,
    })


def airplane_list_view(request):
    name_query = request.GET.get('name')
    airplanes = Airplane.objects.all()
    if name_query:
        airplanes = airplanes.filter(name__icontains=name_query)
    return render(request, 'web/list_airplanes.html', {'airplanes': airplanes})


def airport_list_view(request):
    airports = Airport.objects.all()
    return render(request, 'web/list_airports.html', {'airports': airports})
