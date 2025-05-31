from django.contrib import admin
from django.urls import path, include
from core.views import home, compare_airplanes_view
from web import views
from web.views import flight_view, airport_list_view, airplane_list_view

urlpatterns = [
    path('core/', include('core.urls')),
    path('airports/<int:pk>/', views.AirportDetailView.as_view(), name='airport_detail'),
    path('airplanes/<int:pk>/', views.AirplaneDetailView.as_view(), name='airplane_detail'),
    path('airplanes/', airplane_list_view, name='airplane_list'),
    path('airports/', airport_list_view, name='airport_list'),
    path('compare/', compare_airplanes_view, name='compare_airplanes'),
    path('map/', flight_view, name="map"),
    path('', home, name='home'),
]

