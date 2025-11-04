from django import template
register = template.Library()

@register.filter
def startswith(text, starts):
    """Return True if string starts with the given value."""
    try:
        return str(text).startswith(str(starts))
    except Exception:
        return False
