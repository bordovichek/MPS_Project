from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import redirect, render


def home(request):
    return render(request, "web/home.html")


def custom_404_handler(request, exception):
    return redirect('/')
