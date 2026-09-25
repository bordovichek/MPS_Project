from math import ceil

from django.db.models import Q
from django.db.models.functions import Lower
from rest_framework import status, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from api.serializers import (
    AirplaneSerializer,
    AirportSerializer,
    RouteQuerySerializer,
    route_payload,
    unreachable_payload,
)
from core.models import Airplane, Airport
from core.routing import FlightProfile, InvalidRouteError, RouteUnreachableError, UnknownAirportsError, plan_route


class OptionalLimitOffsetPagination(LimitOffsetPagination):
    """Без ?limit отдаёт весь список, с ?limit=&offset= — страницу."""

    max_limit = 1000


class ApiRootView(APIView):
    def get(self, request, format=None):
        return Response(
            {
                "airplanes": reverse("api:airplane-list", request=request, format=format),
                "airports": reverse("api:airport-list", request=request, format=format),
                "route": reverse("api:route", request=request, format=format) + "?airports=SVO,CDG,JFK&airplane=4",
            }
        )


class AirplaneViewSet(viewsets.ReadOnlyModelViewSet):
    """Самолёты. Фильтры: ?search=boeing, ?in_service=true|false."""

    serializer_class = AirplaneSerializer
    pagination_class = OptionalLimitOffsetPagination

    def get_queryset(self):
        queryset = Airplane.objects.order_by(Lower("name"))
        params = self.request.query_params
        if search := params.get("search", "").strip():
            queryset = queryset.filter(name__icontains=search)
        if (in_service := params.get("in_service", "").lower()) in {"true", "false"}:
            queryset = queryset.filter(in_service=in_service == "true")
        return queryset


class AirportViewSet(viewsets.ReadOnlyModelViewSet):
    """Аэропорты; детальная страница — по IATA-коду. Фильтры: ?search=moscow, ?country=RU."""

    serializer_class = AirportSerializer
    pagination_class = OptionalLimitOffsetPagination
    lookup_field = "iata_code"
    lookup_value_regex = "[A-Za-z]{3}"

    def get_queryset(self):
        queryset = Airport.objects.order_by("iata_code")
        params = self.request.query_params
        if search := params.get("search", "").strip():
            queryset = queryset.filter(Q(name__icontains=search) | Q(iata_code__iexact=search))
        if country := params.get("country", "").strip():
            queryset = queryset.filter(country=country.upper())
        return queryset

    def get_object(self):
        self.kwargs[self.lookup_field] = self.kwargs[self.lookup_field].upper()
        return super().get_object()


class RouteView(APIView):
    """Маршрут через аэропорты с учётом дальности самолёта.

    Параметры: airports=SVO,CDG,JFK (2–8 кодов), airplane=<id> (необязательно), criterion=time|distance|stops.
    Без самолёта строятся прямые перелёты. Если самолёт не долетает даже с дозаправками — ответ 422
    с минимально необходимой дальностью и подходящими самолётами.
    """

    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "route"

    def get(self, request):
        query = RouteQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        airports, airplane, criterion = (query.validated_data.get(key) for key in ("airports", "airplane", "criterion"))

        try:
            plan = plan_route(airports, FlightProfile.of(airplane) if airplane else None, criterion)
        except (UnknownAirportsError, InvalidRouteError) as error:
            raise ValidationError({"airports": [str(error)]}) from error
        except RouteUnreachableError as error:
            suitable = Airplane.objects.filter(max_distance__gte=ceil(error.required_range_km)).order_by(
                "-in_service", "max_distance"
            )[:5]
            return Response(
                unreachable_payload(error, airplane, list(suitable)), status=status.HTTP_422_UNPROCESSABLE_ENTITY
            )
        return Response(route_payload(plan, airplane))
