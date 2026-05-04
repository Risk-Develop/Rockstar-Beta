from django import template
from datetime import date

register = template.Library()


@register.filter
def is_past(value):
    """Check if a date is in the past"""
    if value:
        return value < date.today()
    return False


@register.simple_tag
def get_column_color(column):
    """Get column color"""
    return column.color


@register.filter
def get_status_color(status):
    """Get status color based on status"""
    colors = {
        'backlog': '#6b7280',
        'to_do': '#3b82f6',
        'in_progress': '#f59e0b',
        'review': '#8b5cf6',
        'done': '#10b981',
    }
    return colors.get(status.lower().replace(' ', '_'), '#6b7280')