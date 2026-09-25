from django.core.management.base import BaseCommand, CommandError

from core.openaip import OpenAIPError, import_airports


class Command(BaseCommand):
    help = "Импортирует аэропорты с IATA-кодами из OpenAIP. Существующие записи обновляются."

    def add_arguments(self, parser):
        parser.add_argument("countries", nargs="+", metavar="COUNTRY", help="ISO-коды стран, например RU US DE")
        parser.add_argument("--max-pages", type=int, default=None, help="Ограничить число страниц (по 1000 записей)")
        parser.add_argument("--dry-run", action="store_true", help="Только скачать и проверить, ничего не сохранять")

    def handle(self, *args, countries, max_pages, dry_run, **options):
        for country in countries:
            if len(country) != 2 or not country.isalpha():
                raise CommandError(f"Некорректный код страны: {country!r}")
            try:
                result = import_airports(country, max_pages=max_pages, dry_run=dry_run)
            except OpenAIPError as error:
                raise CommandError(str(error)) from error
            action = "проверено" if dry_run else "сохранено"
            self.stdout.write(
                self.style.SUCCESS(
                    f"{country.upper()}: получено {result.received}, {action} {result.saved}, "
                    f"пропущено без IATA-кода или с ошибками {result.skipped}"
                )
            )
