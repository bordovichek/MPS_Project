from django.core.paginator import EmptyPage, Paginator, PageNotAnInteger
from django.shortcuts import render
from django.db import models
from django.views.generic import DetailView, ListView, TemplateView

from core.models_dir import Airport, Airplane


class FlightView(TemplateView):
    template_name = "web/map.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["airports"] = Airport.objects.all().order_by("name")
        context["aircrafts"] = Airplane.objects.all()
        return context


class AirplaneListView(ListView):
    model = Airplane
    template_name = 'web/list_airplanes.html'
    context_object_name = 'airplanes'

    def get_queryset(self):
        queryset = super().get_queryset()
        name_query = self.request.GET.get('name')
        if name_query:
            queryset = queryset.filter(name__icontains=name_query)
        return queryset


def airport_list_view(request):
    all_airports = Airport.objects.all()
    search_query = request.GET.get('search', '')
    if search_query:
        all_airports = all_airports.filter(
            models.Q(name__icontains=search_query) | models.Q(iata_code__icontains=search_query)
        ).distinct()
    sort_by = request.GET.get('sort_by', 'name')
    order_by_fields = []

    if sort_by == 'name':
        order_by_fields.append('name')
    elif sort_by == 'iata_code':
        order_by_fields.append('iata_code')
    elif sort_by == 'country':
        order_by_fields.append('country')
        order_by_fields.append('name')
    all_airports = all_airports.order_by(*order_by_fields)
    paginator = Paginator(all_airports, 50)
    page_number = request.GET.get('page')
    try:
        page_obj = paginator.get_page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.get_page(1)
    except EmptyPage:
        page_obj = paginator.get_page(paginator.num_pages)

    return render(request, 'web/list_airports.html', {
        'airports': page_obj,
        'search_query': search_query,
        'sort_by': sort_by,
    })


class AirportDetailView(DetailView):
    model = Airport
    template_name = 'web/airport_detail.html'
    context_object_name = 'airport'


class AirplaneDetailView(DetailView):
    model = Airplane
    template_name = 'web/airplane_detail.html'
    context_object_name = 'airplane'
