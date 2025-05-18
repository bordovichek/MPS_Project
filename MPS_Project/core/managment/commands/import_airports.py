from django.core.management.base import BaseCommand
from core.services_dir.openaip_import import get_airports_from_openaip


class Command(BaseCommand):
    help = 'Импорт аэропортов из OpenAIP API'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=20)
        parser.add_argument('--country', type=str, default='RU')

    def handle(self, *args, **options):
        limit = options['limit']
        country = options['country']
        get_airports_from_openaip(limit=limit, country_code=country)
        self.stdout.write(self.style.SUCCESS(f"Аэропорты {country} загружены."))
