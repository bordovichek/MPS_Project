from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import redirect
from django.urls import reverse

def home(request):
    html = """
    <h1>Добро пожаловать на главную страницу</h1>
    <p>Перейдите к списку:</p>
    <ul>
        <li><a href="/airplanes/">Список самолетов</a></li>
        <li><a href="/airports/">Список аэропортов</a></li>
    </ul>
    """
    return HttpResponse(html)

def custom_404_handler(request, exception):
    # Редирект на главную страницу
    return redirect('/')