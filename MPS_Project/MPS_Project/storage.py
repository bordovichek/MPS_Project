from django.contrib.staticfiles.storage import ManifestStaticFilesStorage


class StaticStorage(ManifestStaticFilesStorage):
    """Хэши в именах файлов + переписывание `import … from "./x.js"` в ES-модулях на хэшированные имена."""

    support_js_module_import_aggregation = True
