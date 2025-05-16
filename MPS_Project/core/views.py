from rest_framework import generics

from .mixins import CaseInsensitiveLookupMixin
from .models_dir import Airplane, Airport
from .serializers import AirplaneSerializer, AirportSerializer


class AirplaneListView(generics.ListAPIView):
    queryset = Airplane.objects.all()
    serializer_class = AirplaneSerializer


class AirportListView(generics.ListAPIView):
    queryset = Airport.objects.all()
    serializer_class = AirportSerializer


class AirplaneDetailView(CaseInsensitiveLookupMixin, generics.RetrieveAPIView):
    queryset = Airplane.objects.all()
    serializer_class = AirplaneSerializer
    lookup_field = "name"


class AirportDetailView(CaseInsensitiveLookupMixin, generics.RetrieveAPIView):
    queryset = Airport.objects.all()
    serializer_class = AirportSerializer
    lookup_field = "iata_code"
