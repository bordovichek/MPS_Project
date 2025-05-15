from django.shortcuts import render
from core.models import Airplane

def airplane_list(request):
    airplanes = Airplane.objects.all()
    return render(request, 'web/airplane_list.html', {'airplanes': airplanes})
