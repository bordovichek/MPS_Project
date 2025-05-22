from django.urls import path, include
from rest_framework.routers import DefaultRouter
from api import views

router = DefaultRouter()

urlpatterns = [
    path('', include(router.urls)),
    path('calculate_route/', views.calculate_route, name='calculate_route'),
]
