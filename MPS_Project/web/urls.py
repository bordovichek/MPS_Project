from django.contrib import admin
from django.urls import path, include

from core.views import home
from web.views import flight_view

urlpatterns = [
    path('', home, name='home'),
    path('', include('core.urls')),
    path("map/", flight_view, name="map"),
]
