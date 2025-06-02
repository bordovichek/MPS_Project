from django.contrib import admin
from django.urls import path, include
from django.views.decorators.cache import cache_page

from api.views import AirportListView
from core.views import compare_airplanes_view, Home
from web import views

urlpatterns = [
    path('core/', include('core.urls')),
    path('airports/<int:pk>/', views.AirportDetailView.as_view(), name='airport_detail'),
    path('airplanes/<int:pk>/', views.AirplaneDetailView.as_view(), name='airplane_detail'),
    path('airplanes/', cache_page(300)(views.AirplaneListView.as_view()), name='airplane_list'),
    path('airports/', views.airport_list_view, name='airport_list'),
    path('compare/', compare_airplanes_view, name='compare_airplanes'),
    path('map/', cache_page(300)(views.FlightView.as_view()), name="map"),
    path('', cache_page(300)(Home.as_view()), name='home'),
]

