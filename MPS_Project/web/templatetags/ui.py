from django import template
from django.templatetags.static import static
from django.utils.html import format_html
from django_countries import countries

register = template.Library()


@register.simple_tag
def icon(name: str, css_class: str = "") -> str:
    return format_html(
        '<svg class="icon {}" aria-hidden="true" focusable="false"><use href="{}#i-{}"></use></svg>',
        css_class,
        static("web/img/icons.svg"),
        name,
    )


@register.simple_tag(takes_context=True)
def nav_active(context, *url_names: str) -> str:
    match = getattr(context.get("request"), "resolver_match", None)
    return "is-active" if match and match.url_name in url_names else ""


@register.filter
def duration(hours: float | None) -> str:
    """3.75 → «3 ч 45 мин»."""
    if hours is None:
        return "—"
    total = round(hours * 60)
    h, m = divmod(total, 60)
    if not h:
        return f"{m} мин"
    return f"{h} ч {m:02d} мин" if m else f"{h} ч"


@register.filter
def flag(code: str) -> str:
    code = str(code).upper()
    if len(code) != 2 or not code.isalpha():
        return ""
    return "".join(chr(0x1F1E6 + ord(letter) - ord("A")) for letter in code)


@register.filter
def country_name(code: str) -> str:
    return countries.name(str(code)) or str(code)


@register.simple_tag
def coords(latitude: float, longitude: float, digits: int = 4) -> str:
    """Координаты в привычном для карт виде: «55.9726, 37.4146» (без локализации запятой)."""
    return f"{latitude:.{digits}f}, {longitude:.{digits}f}"
