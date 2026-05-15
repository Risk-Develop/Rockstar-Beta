from django import template
from django.urls import reverse

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

@register.filter
def status_badge_class(interview, status_field):
    """Get status badge CSS class for a given status field."""
    return interview.get_status_badge_class(status_field)

@register.filter
def qualitative_insight(interview, key):
    """Get qualitative insight value for a given key."""
    return interview.get_qualitative_insight(key)

@register.filter
def get_status_field_display(interview, field_name):
    """Dynamically call get_<field_name>_display on an interview instance."""
    method = getattr(interview, f'get_{field_name}_display', None)
    return method() if method else ''

@register.simple_tag
def bulk_mark_all_read_url():
    """URL for the bulk mark-all-as-read / all-visible-as-completed endpoint."""
    return reverse('human_resource:exit_interview_bulk_mark_all_read')

@register.simple_tag
def bulk_status_update_url():
    """URL for the bulk status update endpoint."""
    return reverse('human_resource:exit_interview_bulk_status_update')

@register.simple_tag
def satisfaction_chart_data_url(pk):
    """URL for satisfaction chart data for a specific interview."""
    return reverse('human_resource:exit_interview_satisfaction_chart', args=[pk])

