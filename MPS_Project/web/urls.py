from django.urls import path

from web import views

app_name = "web"

urlpatterns = [
    path("", views.HomeView.as_view(), name="home"),
    path("map/", views.RoutePlannerView.as_view(), name="planner"),
    path("airplanes/", views.AirplaneListView.as_view(), name="airplane_list"),
    path("airplanes/<int:pk>/", views.AirplaneDetailView.as_view(), name="airplane_detail"),
    path("airports/", views.AirportListView.as_view(), name="airport_list"),
    path("airports/<str:iata>/", views.AirportDetailView.as_view(), name="airport_detail"),
    path("compare/", views.CompareView.as_view(), name="compare"),
]
