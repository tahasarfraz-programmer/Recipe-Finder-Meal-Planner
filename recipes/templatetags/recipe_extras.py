from django import template
from django.utils.html import format_html
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag
def stars(value):
    """Render five Bootstrap star icons for a 0-5 rating."""
    try:
        v = float(value or 0)
    except (TypeError, ValueError):
        v = 0.0
    icons = []
    for i in range(1, 6):
        if v >= i - 0.25:
            icons.append('<i class="bi bi-star-fill"></i>')
        elif v >= i - 0.75:
            icons.append('<i class="bi bi-star-half"></i>')
        else:
            icons.append('<i class="bi bi-star"></i>')
    return format_html('<span class="stars" aria-hidden="true">{}</span>', mark_safe("".join(icons)))


@register.simple_tag(takes_context=True)
def url_replace(context, **kwargs):
    """Current query string with some params replaced/removed (for pagination)."""
    query = context["request"].GET.copy()
    for key, value in kwargs.items():
        if value in (None, ""):
            query.pop(key, None)
        else:
            query[key] = value
    return query.urlencode()


@register.filter
def dict_get(mapping, key):
    return mapping.get(key)
