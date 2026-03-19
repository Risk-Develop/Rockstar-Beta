from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)

@register.filter
def split(value, delimiter):
    """Split a string by delimiter and return a list"""
    if not value:
        return []
    return [item.strip() for item in value.split(delimiter)]

@register.filter
def format_status(value):
    """Format status value: replace underscores with spaces and title case"""
    if not value:
        return ''
    return value.replace('_', ' ').title()

@register.filter
def get_initials(first_name, last_name):
    """Get initials from first name and last name"""
    first_initial = ''
    last_initial = ''
    if first_name:
        first_initial = first_name[0].upper() if len(first_name) > 0 else ''
    if last_name:
        last_initial = last_name[0].upper() if len(last_name) > 0 else ''
    return first_initial + last_initial

