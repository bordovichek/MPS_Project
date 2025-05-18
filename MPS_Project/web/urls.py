from django.contrib import admin
from django.urls import path, include

from core.views import home

urlpatterns = [
    path('', home, name='home'),
    path('', include('core.urls')),
]
