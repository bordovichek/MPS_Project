from rest_framework.exceptions import NotFound


class CaseInsensitiveLookupMixin:
    """Миксин для того чтобы у нас поиск был нечувствителен к регистру"""
    lookup_field = None

    def get_object(self):
        if self.lookup_field is None:
            raise AttributeError("Укажите 'lookup_field' в классе представления")

        lookup_value = self.kwargs.get(self.lookup_field)
        filter_kwargs = {f"{self.lookup_field}__iexact": lookup_value}

        model_class = self.get_queryset().model
        try:
            return model_class.objects.get(**filter_kwargs)
        except model_class.DoesNotExist:
            raise NotFound(f"{model_class.__name__} с {self.lookup_field}='{lookup_value}' не найден.")
