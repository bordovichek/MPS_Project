from django.contrib import admin
from django.urls import path, include
from core.views import home
from web.views import flight_view, airport_list_view, airplane_list_view

urlpatterns = [
    path('core/', include('core.urls')),
    path('airplanes/', airplane_list_view, name='airplane_list'),
    path('airports/', airport_list_view, name='airport_list'),
    path('map/', flight_view, name="map"),
    path('', home, name='home'),
]

