from django import template

register = template.Library()

@register.filter
def dict_get(d, key):
    """Allows dictionary access in templates: {{ mydict|dict_get:key }}"""
    if not isinstance(d, dict):
        return None
    return d.get(key)

@register.filter
def list_get(seq, index):
    """Allows list/tuple index access in templates: {{ mylist|list_get:i }}"""
    if not isinstance(seq, (list, tuple)):
        return None
    try:
        return seq[int(index)]
    except (ValueError, IndexError, TypeError):
        return None

@register.filter
def div(value, arg):
    """Divides the value by the argument. Usage: {{ value|div:2 }}"""
    try:
        return float(value) / float(arg)
    except (ValueError, ZeroDivisionError, TypeError):
        return 0.0

@register.filter
def mul(value, arg):
    """Multiplies the value by the argument. Usage: {{ value|mul:2 }}"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0.0