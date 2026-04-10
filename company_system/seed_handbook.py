#!/usr/bin/env python
"""Seed script for handbook compliance data"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sub_company_system.settings')
django.setup()

from App.human_resource.handbook_models import ViolationCategory, ViolationType, RemedialAction

# Create categories
cats = [
    ('CAR', 'Corrective Action Request', 1),
    ('Violation', 'General Violation', 2),
    ('Client Case', 'Client-related incident', 3),
    ('Pending', 'Pending case', 4),
    ('NTE', 'Notice to Explain', 5),
]
for name, desc, order in cats:
    ViolationCategory.objects.get_or_create(
        name=name,
        defaults={'description': desc, 'display_order': order, 'is_active': True}
    )

# Create types
types_list = [
    ('Client - Related', 'Incidents related to clients', 1),
    ('Discipline - Related', 'Disciplinary issues', 2),
    ('Performance - Related', 'Performance-related issues', 3),
    ('Pending', 'Pending classification', 4),
]
for name, desc, order in types_list:
    ViolationType.objects.get_or_create(
        name=name,
        defaults={'description': desc, 'display_order': order, 'is_active': True}
    )

# Create remedial actions
actions = [
    ('A', 1, 'Verbal Warning', 'Oral counseling and warning'),
    ('A', 2, 'Written Warning', 'Formal written warning in file'),
    ('A', 3, 'Suspension 1-3 Days', 'Suspension without pay for 1-3 working days'),
    ('A', 4, 'Suspension 4-6 Days', 'Suspension without pay for 4-6 working days'),
    ('A', 5, 'Dismissal', 'Termination of employment'),
    ('B', 1, 'Written Warning', 'Formal written warning in file'),
    ('B', 2, 'Suspension 1-3 Days', 'Suspension without pay for 1-3 working days'),
    ('B', 3, 'Suspension 4-6 Days', 'Suspension without pay for 4-6 working days'),
    ('B', 4, 'Dismissal', 'Termination of employment'),
    ('C', 1, 'Suspension 1-3 Days', 'Suspension without pay for 1-3 working days'),
    ('C', 2, 'Suspension 4-6 Days', 'Suspension without pay for 4-6 working days'),
    ('C', 3, 'Dismissal', 'Termination of employment'),
    ('D', 1, 'Dismissal', 'Immediate termination of employment'),
]
for range_code, count, action, details in actions:
    RemedialAction.objects.get_or_create(
        range_code=range_code,
        offense_count=count,
        defaults={'action': action, 'action_details': details, 'is_active': True}
    )

print(f'Categories: {ViolationCategory.objects.count()}')
print(f'Types: {ViolationType.objects.count()}')
print(f'Actions: {RemedialAction.objects.count()}')