from django.urls import path, include
from rest_framework.routers import DefaultRouter
from api.views import AirplaneDetailView, AirplaneListView, AirportDetailView, AirportListView
from core.views import calculate_route_view, get_initial_data_view

router = DefaultRouter()

urlpatterns = [
    path('', include(router.urls)),
    path('airplanes/<str:name>/', AirplaneDetailView.as_view(), name='airplane-detail'),
    path('airplanes/', AirplaneListView.as_view(), name='airplanes-list'),
    path('airports/<str:iata_code>/', AirportDetailView.as_view(), name='airport-detail'),
    path('airports/', AirportListView.as_view(), name='airports-list'),
    path('calculate_route/', calculate_route_view, name='calculate_route'),
    path('initial_data/', get_initial_data_view, name='initial_data'),
]
