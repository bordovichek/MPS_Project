from django.urls import path
from .views import airplane_list

urlpatterns = [
    path('', airplane_list, name='airplane_list'),
]
