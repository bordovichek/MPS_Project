from django.urls import path
from .views import AirplaneListView, AirportListView

urlpatterns = [
    path('airplanes/', AirplaneListView.as_view(), name='airplanes-list'),
    path('airports/', AirportListView.as_view(), name='airports-list'),
]
