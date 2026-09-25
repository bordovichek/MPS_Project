from django.db.models import Case, CharField, Count, F, Q, Value, When
from django.db.models.functions import Lower
from django.shortcuts import get_object_or_404
from django.templatetags.static import static
from django.urls import reverse
from django.views.generic import DetailView, ListView, TemplateView
from django_countries import countries

from core.models import Airplane, Airport
from core.routing import MAX_WAYPOINTS, AirportIndex, Criterion
from web.comparison import build_comparison

EXAMPLE_ROUTES = (
    ("SVO", "JFK", "Airbus A320neo", "Через Атлантику на узкофюзеляжном самолёте — с одной дозаправкой"),
    ("LED", "CPT", "Boeing 737-800", "Из Петербурга в Кейптаун: две промежуточные посадки"),
    ("SVO", "LAX", "ATR 72-600", "Турбовинтовой ATR через Сибирь, Чукотку и Аляску"),
    ("SVO", "ADL", "Boeing 787-9 Dreamliner", "Москва — Аделаида без посадок: почти 14 000 км"),
)


class HomeView(TemplateView):
    template_name = "web/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["stats"] = {
            "airports": Airport.objects.count(),
            "countries": Airport.objects.values("country").distinct().count(),
            "airplanes": Airplane.objects.count(),
        }
        context["examples"] = self._examples()
        context["max_waypoints"] = MAX_WAYPOINTS
        return context

    @staticmethod
    def _examples() -> list[dict]:
        index = AirportIndex.current()
        airplanes = dict(Airplane.objects.values_list("name", "pk"))
        examples = []
        for origin, destination, airplane, note in EXAMPLE_ROUTES:
            if origin not in index or destination not in index or airplane not in airplanes:
                continue
            examples.append(
                {
                    "origin": index.airport(index.position(origin)),
                    "destination": index.airport(index.position(destination)),
                    "airplane": airplane,
                    "note": note,
                    "url": f"{reverse('web:planner')}?route={origin},{destination}&plane={airplanes[airplane]}",
                }
            )
        return examples


class AirplaneListView(ListView):
    template_name = "web/airplane_list.html"
    context_object_name = "airplanes"
    sorts = {
        "name": ("По названию", [Lower("name")]),
        "-max_distance": ("Сначала дальнемагистральные", [F("max_distance").desc()]),
        "max_distance": ("Сначала ближнемагистральные", [F("max_distance").asc()]),
        "-capacity": ("Самые вместительные", [F("capacity").desc(nulls_last=True)]),
        "-cruise_speed": ("Самые быстрые", [F("cruise_speed").desc()]),
        "consumption": ("Самый низкий расход", [F("consumption").asc()]),
        "-year_of_manufacture": ("Сначала новые", [F("year_of_manufacture").desc(nulls_last=True)]),
        "year_of_manufacture": ("Сначала старые", [F("year_of_manufacture").asc(nulls_last=True)]),
    }
    statuses = {"": "Все", "active": "В эксплуатации", "retired": "Выведены"}

    def get_queryset(self):
        params = self.request.GET
        self.query = params.get("q", "").strip()
        self.status = params.get("status", "") if params.get("status") in self.statuses else ""
        self.sort = params.get("sort", "name") if params.get("sort") in self.sorts else "name"

        queryset = Airplane.objects.all()
        if self.query:
            queryset = queryset.filter(Q(name__icontains=self.query) | Q(engines__icontains=self.query))
        if self.status:
            queryset = queryset.filter(in_service=self.status == "active")
        return queryset.order_by(*self.sorts[self.sort][1], Lower("name"))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            query=self.query,
            status=self.status,
            sort=self.sort,
            sort_options={key: label for key, (label, _) in self.sorts.items()},
            status_options=self.statuses,
            total=Airplane.objects.count(),
        )
        return context


class AirplaneDetailView(DetailView):
    model = Airplane
    template_name = "web/airplane_detail.html"
    context_object_name = "airplane"
    reference_routes = (
        ("SVO", "AER", "Москва — Сочи"),
        ("SVO", "DXB", "Москва — Дубай"),
        ("SVO", "JFK", "Москва — Нью-Йорк"),
        ("SVO", "LAX", "Москва — Лос-Анджелес"),
        ("SVO", "ADL", "Москва — Аделаида"),
    )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        airplane = self.object
        others = Airplane.objects.exclude(pk=airplane.pk)
        context["similar"] = sorted(others, key=lambda plane: abs(plane.max_distance - airplane.max_distance))[:3]
        context["reach"] = self._reach(airplane)
        return context

    def _reach(self, airplane: Airplane) -> list[dict]:
        """Контрольные маршруты: долетит ли самолёт без посадки и какую часть пути покрывает его дальность."""
        index = AirportIndex.current()
        planner = reverse("web:planner")
        items = []
        for origin, destination, title in self.reference_routes:
            if origin not in index or destination not in index:
                continue
            distance = index.distance_km(index.position(origin), index.position(destination))
            items.append(
                {
                    "title": title,
                    "distance": round(distance),
                    "nonstop": airplane.max_distance >= distance,
                    "share": min(1.0, airplane.max_distance / distance),
                    "url": f"{planner}?route={origin},{destination}&plane={airplane.pk}",
                }
            )
        return items


class AirportListView(ListView):
    template_name = "web/airport_list.html"
    context_object_name = "airports"
    paginate_by = 30
    sorts = {"name": "По названию", "iata_code": "По IATA-коду", "country": "По стране"}

    def get_queryset(self):
        params = self.request.GET
        self.query = params.get("q", "").strip()
        self.country = params.get("country", "").strip().upper()
        self.sort = params.get("sort", "name") if params.get("sort") in self.sorts else "name"

        queryset = Airport.objects.all()
        if self.query:
            queryset = queryset.filter(Q(name__icontains=self.query) | Q(iata_code__iexact=self.query))
        if self.country:
            queryset = queryset.filter(country=self.country)
        if self.sort == "country":
            return queryset.order_by(self._country_name_expression(), "name")
        return queryset.order_by(self.sort)

    @staticmethod
    def _country_name_expression() -> Case:
        """Сортировка по русскому названию страны, а не по ISO-коду."""
        codes = Airport.objects.values_list("country", flat=True).distinct()
        return Case(
            *(When(country=code, then=Value(countries.name(code))) for code in codes),
            default=F("country"),
            output_field=CharField(),
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        per_country = Airport.objects.values("country").annotate(total=Count("pk")).order_by()
        country_options = sorted(
            (
                {"code": row["country"], "name": countries.name(row["country"]), "total": row["total"]}
                for row in per_country
            ),
            key=lambda option: option["name"],
        )
        context.update(
            query=self.query,
            country=self.country,
            sort=self.sort,
            sort_options=self.sorts,
            country_options=country_options,
        )
        if page := context.get("page_obj"):
            context["page_range"] = page.paginator.get_elided_page_range(page.number, on_each_side=1, on_ends=1)
        return context


class AirportDetailView(DetailView):
    template_name = "web/airport_detail.html"
    context_object_name = "airport"

    def get_object(self, queryset=None):
        return get_object_or_404(Airport, iata_code=self.kwargs["iata"].upper())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        index = AirportIndex.current()
        code = self.object.iata_code
        context["nearest"] = index.nearest(code) if code in index else []
        context["map_data"] = {
            "airport": [self.object.latitude, self.object.longitude, code],
            "nearest": [[ref.latitude, ref.longitude, ref.iata_code] for ref, _ in context["nearest"]],
            "landUrl": static("web/data/land-110m.geojson"),
            "airportUrl": reverse("web:airport_detail", args=["XXX"]),
        }
        return context


class CompareView(TemplateView):
    template_name = "web/compare.html"
    max_airplanes = 3

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ids = []
        for raw in self.request.GET.getlist("ids"):
            for part in raw.split(","):
                if part.strip().isdigit() and int(part) not in ids:
                    ids.append(int(part))
        found = Airplane.objects.in_bulk(ids[: self.max_airplanes])
        selected = [found[pk] for pk in ids if pk in found]

        context.update(
            selected=selected,
            slots=[selected[i] if i < len(selected) else None for i in range(self.max_airplanes)],
            airplanes=Airplane.objects.order_by(Lower("name")),
            rows=build_comparison(selected) if len(selected) >= 2 else [],
        )
        return context


class RoutePlannerView(TemplateView):
    template_name = "web/planner.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        index = AirportIndex.current()
        airplanes = Airplane.objects.order_by("-in_service", Lower("name"))
        context["planner_data"] = {
            "airports": [
                [code, name, country, round(float(lat), 4), round(float(lon), 4)]
                for code, name, country, lat, lon in zip(
                    index.codes, index.names, index.countries, index.lat, index.lon, strict=True
                )
            ],
            "countries": {code: countries.name(code) for code in set(index.countries)},
            "airplanes": [
                {
                    "id": plane.pk,
                    "name": plane.name,
                    "range": plane.max_distance,
                    "speed": plane.cruise_speed,
                    "inService": plane.in_service,
                }
                for plane in airplanes
            ],
            "criteria": [{"value": value, "label": label} for value, label in Criterion.choices],
            "maxWaypoints": MAX_WAYPOINTS,
            "urls": {
                "route": reverse("api:route"),
                "airport": reverse("web:airport_detail", args=["XXX"]),
                "airplane": reverse("web:airplane_detail", args=[0]),
                "land": static("web/data/land-110m.geojson"),
            },
        }
        return context
