from django import template

register = template.Library()

@register.filter
def replace(value, arg):
    """
    Replace occurrences of arg in value.
    Usage: {{ value|replace:"old:new" }}
    """
    if not value:
        return value
    if ':' not in arg:
        return value
    old, new = arg.split(':', 1)
    return value.replace(old, new)