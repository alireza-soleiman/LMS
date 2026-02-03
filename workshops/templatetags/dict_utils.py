from django import template

register = template.Library()

@register.filter
def dict_get(d, key):
    """Allows dictionary access in templates: {{ mydict|dict_get:key }}"""
    if not isinstance(d, dict):
        return None
    return d.get(key)
