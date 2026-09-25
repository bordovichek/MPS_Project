from django.urls import path
from rest_framework.routers import SimpleRouter

from api import views

app_name = "api"

router = SimpleRouter()
router.register("airplanes", views.AirplaneViewSet, basename="airplane")
router.register("airports", views.AirportViewSet, basename="airport")

urlpatterns = [
    path("", views.ApiRootView.as_view(), name="root"),
    path("route/", views.RouteView.as_view(), name="route"),
    *router.urls,
]
