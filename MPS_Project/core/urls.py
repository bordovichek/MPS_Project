from django.urls import path
from .views import AirplaneListView, AirportListView, AirplaneDetailView, AirportDetailView

urlpatterns = [
    path('airplanes/<str:name>/', AirplaneDetailView.as_view(), name='airplane-detail'),
    path('airplanes/', AirplaneListView.as_view(), name='airplanes-list'),
    path('airports/<str:iata_code>/', AirportDetailView.as_view(), name='airport-detail'),
    path('airports/', AirportListView.as_view(), name='airports-list'),
]
