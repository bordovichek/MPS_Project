from rest_framework import generics

from MPS_Project.core.mixins import CaseInsensitiveLookupMixin
from MPS_Project.core.models_dir import Airplane, Airport
from MPS_Project.core.serializers import AirplaneSerializer, AirportSerializer


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
