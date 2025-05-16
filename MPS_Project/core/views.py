from rest_framework import generics
from .models_dir import Airplane, Airport
from .serializers import AirplaneSerializer, AirportSerializer


class AirplaneListView(generics.ListAPIView):
    queryset = Airplane.objects.all()
    serializer_class = AirplaneSerializer


class AirportListView(generics.ListAPIView):
    queryset = Airport.objects.all()
    serializer_class = AirportSerializer


class AirplaneDetailView(generics.RetrieveAPIView):
    queryset = Airplane.objects.all()
    serializer_class = AirplaneSerializer
    lookup_field = "name"


class AirportDetailView(generics.RetrieveAPIView):
    queryset = Airport.objects.all()
    serializer_class = AirportSerializer
    lookup_field = "iata_code"  # Поиск по IATA-коду
