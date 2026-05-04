"""
Handbook Offense Classification & Compliance Views
=====================================================

This module contains views for:
1. Offense Groups (Rule 1, Rule 2, etc.)
2. Offense Sections (1.1, 1.2, etc.)
3. Offense Classifications (Infraction/Violation descriptions)
4. Remedial Action Settings
5. Violation Categories (CAR, Violation, Client Case, Pending, NTE)
6. Violation Types (Client-Related, Discipline-Related, Performance-Related, Pending)
7. Employee Violations (Track violations per employee)
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from App.authentication.decorators import login_required
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.db.models import Q

from App.users.models import Staff
from .handbook_models import (
    OffenseGroup,
    OffenseSection,
    OffenseClassification,
    RemedialAction,
    ViolationCategory,
    ViolationType,
    EmployeeViolation,
)


# =============================================================================
# OFFENSE GROUP VIEWS
# =============================================================================

@login_required
def offense_group_list(request):
    """List all offense groups"""
    search = request.GET.get('search', '').strip()
    groups = OffenseGroup.objects.all().order_by('group_number')
    
    if search:
        groups = groups.filter(
            Q(group_number__icontains=search) | 
            Q(group_name__icontains=search)
        )
    
    paginator = Paginator(groups, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'hr/default/compliance & offense management/handbook/offense_group_list.html', {
        'page_obj': page_obj,
        'search': search,
    })


@login_required
def offense_group_add(request):
    """Add new offense group"""
    if request.method == 'POST':
        group_number = request.POST.get('group_number')
        group_name = request.POST.get('group_name')
        description = request.POST.get('description', '')
        is_active = request.POST.get('is_active') == 'on'
        if not is_active:
            is_active = True  # Default to True if not explicitly unchecked
        
        if OffenseGroup.objects.filter(group_number=group_number).exists():
            messages.error(request, 'Group number already exists.')
            return render(request, 'hr/default/compliance & offense management/handbook/offense_group_form.html', {
                'action': 'Add',
                'group': {'group_number': group_number, 'group_name': group_name, 'description': description, 'is_active': is_active}
            })
        
        OffenseGroup.objects.create(
            group_number=group_number,
            group_name=group_name,
            description=description,
            is_active=is_active,
        )
        messages.success(request, 'Offense group created successfully.')
        return redirect('human_resource:violation_list')
    
    return render(request, 'hr/default/compliance & offense management/handbook/offense_group_form.html', {
        'action': 'Add',
    })


@login_required
def offense_group_edit(request, pk):
    """Edit offense group"""
    group = get_object_or_404(OffenseGroup, pk=pk)
    
    if request.method == 'POST':
        group_number = request.POST.get('group_number')
        group_name = request.POST.get('group_name')
        description = request.POST.get('description', '')
        is_active = request.POST.get('is_active') == 'on'
        
        if OffenseGroup.objects.filter(group_number=group_number).exclude(pk=pk).exists():
            messages.error(request, 'Group number already exists.')
            return render(request, 'hr/default/compliance & offense management/handbook/offense_group_form.html', {
                'action': 'Edit',
                'group': group
            })
        
        group.group_number = group_number
        group.group_name = group_name
        group.description = description
        group.is_active = is_active
        group.save()
        
        messages.success(request, 'Offense group updated successfully.')
        return redirect('human_resource:offense_group_list')
    
    return render(request, 'hr/default/compliance & offense management/handbook/offense_group_form.html', {
        'action': 'Edit',
        'group': group
    })


@login_required
def offense_group_delete(request, pk):
    """Delete offense group"""
    group = get_object_or_404(OffenseGroup, pk=pk)
    
    if request.method == 'POST':
        group.delete()
        messages.success(request, 'Offense group deleted successfully.')
    else:
        group.delete()
        messages.success(request, 'Offense group deleted successfully.')
    return redirect('human_resource:violation_list')


# =============================================================================
# OFFENSE SECTION VIEWS
# =============================================================================

@login_required
def offense_section_list(request):
    """List all offense sections"""
    search = request.GET.get('search', '').strip()
    group_filter = request.GET.get('group', '')
    
    sections = OffenseSection.objects.select_related('offense_group').all()
    
    if search:
        sections = sections.filter(
            Q(section_number__icontains=search) | 
            Q(section_title__icontains=search)
        )
    
    if group_filter:
        sections = sections.filter(offense_group_id=group_filter)
    
    sections = sections.order_by('offense_group', 'section_number')
    
    paginator = Paginator(sections, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    groups = OffenseGroup.objects.filter(is_active=True).order_by('group_number')
    
    return render(request, 'hr/default/compliance & offense management/handbook/offense_section_list.html', {
        'page_obj': page_obj,
        'search': search,
        'group_filter': group_filter,
        'groups': groups,
    })


@login_required
def offense_section_add(request):
    """Add new offense section"""
    groups = OffenseGroup.objects.filter(is_active=True).order_by('group_number')
    
    if request.method == 'POST':
        section_number = request.POST.get('section_number')
        section_title = request.POST.get('section_title')
        offense_group_id = request.POST.get('offense_group')
        description = request.POST.get('description', '')
        is_active = request.POST.get('is_active') == 'on'
        if not is_active:
            is_active = True  # Default to True
        
        offense_group = get_object_or_404(OffenseGroup, pk=offense_group_id)
        
        OffenseSection.objects.create(
            section_number=section_number,
            section_title=section_title,
            offense_group=offense_group,
            description=description,
            is_active=is_active,
        )
        messages.success(request, 'Offense section created successfully.')
        return redirect('human_resource:violation_list')
    
    return render(request, 'hr/default/compliance & offense management/handbook/offense_section_form.html', {
        'action': 'Add',
        'groups': groups,
    })


@login_required
def offense_section_edit(request, pk):
    """Edit offense section"""
    section = get_object_or_404(OffenseSection, pk=pk)
    groups = OffenseGroup.objects.filter(is_active=True).order_by('group_number')
    
    if request.method == 'POST':
        section_number = request.POST.get('section_number')
        section_title = request.POST.get('section_title')
        offense_group_id = request.POST.get('offense_group')
        description = request.POST.get('description', '')
        is_active = request.POST.get('is_active') == 'on'
        
        offense_group = get_object_or_404(OffenseGroup, pk=offense_group_id)
        
        section.section_number = section_number
        section.section_title = section_title
        section.offense_group = offense_group
        section.description = description
        section.is_active = is_active
        section.save()
        
        messages.success(request, 'Offense section updated successfully.')
        return redirect('human_resource:offense_section_list')
    
    return render(request, 'hr/default/compliance & offense management/handbook/offense_section_form.html', {
        'action': 'Edit',
        'section': section,
        'groups': groups,
    })


@login_required
def offense_section_delete(request, pk):
    """Delete offense section"""
    section = get_object_or_404(OffenseSection, pk=pk)
    
    if request.method == 'POST':
        section.delete()
        messages.success(request, 'Offense section deleted successfully.')
    else:
        section.delete()
        messages.success(request, 'Offense section deleted successfully.')
    return redirect('human_resource:violation_list')


# =============================================================================
# OFFENSE CLASSIFICATION VIEWS
# =============================================================================

@login_required
def classification_list(request):
    """List all offense classifications"""
    search = request.GET.get('search', '').strip()
    section_filter = request.GET.get('section', '')
    range_filter = request.GET.get('range', '')
    
    classifications = OffenseClassification.objects.select_related(
        'offense_section__offense_group'
    ).all()
    
    if search:
        classifications = classifications.filter(offense_description__icontains=search)
    
    if section_filter:
        classifications = classifications.filter(offense_section_id=section_filter)
    
    if range_filter:
        classifications = classifications.filter(default_range=range_filter)
    
    classifications = classifications.order_by('offense_section', 'id')
    
    paginator = Paginator(classifications, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    sections = OffenseSection.objects.filter(is_active=True).select_related('offense_group').order_by('offense_group', 'section_number')
    
    return render(request, 'hr/default/compliance & offense management/handbook/classification_list.html', {
        'page_obj': page_obj,
        'search': search,
        'section_filter': section_filter,
        'range_filter': range_filter,
        'sections': sections,
    })


@login_required
def classification_add(request):
    """Add new offense classification"""
    sections = OffenseSection.objects.filter(is_active=True).select_related('offense_group').order_by('offense_group', 'section_number')
    
    if request.method == 'POST':
        offense_section_id = request.POST.get('offense_section')
        offense_description = request.POST.get('offense_description')
        default_range = request.POST.get('default_range')
        is_active = request.POST.get('is_active') == 'on'
        if not is_active:
            is_active = True  # Default to True
        
        offense_section = get_object_or_404(OffenseSection, pk=offense_section_id)
        
        OffenseClassification.objects.create(
            offense_section=offense_section,
            offense_description=offense_description,
            default_range=default_range,
            is_active=is_active,
        )
        messages.success(request, 'Offense classification created successfully.')
        return redirect('human_resource:violation_list')
    
    return render(request, 'hr/default/compliance & offense management/handbook/classification_form.html', {
        'action': 'Add',
        'sections': sections,
    })


@login_required
def classification_edit(request, pk):
    """Edit offense classification"""
    classification = get_object_or_404(OffenseClassification, pk=pk)
    sections = OffenseSection.objects.filter(is_active=True).select_related('offense_group').order_by('offense_group', 'section_number')
    
    if request.method == 'POST':
        offense_section_id = request.POST.get('offense_section')
        offense_description = request.POST.get('offense_description')
        default_range = request.POST.get('default_range')
        is_active = request.POST.get('is_active') == 'on'
        
        offense_section = get_object_or_404(OffenseSection, pk=offense_section_id)
        
        classification.offense_section = offense_section
        classification.offense_description = offense_description
        classification.default_range = default_range
        classification.is_active = is_active
        classification.save()
        
        messages.success(request, 'Offense classification updated successfully.')
        return redirect('human_resource:classification_list')
    
    return render(request, 'hr/default/compliance & offense management/handbook/classification_form.html', {
        'action': 'Edit',
        'classification': classification,
        'sections': sections,
    })


@login_required
def classification_delete(request, pk):
    """Delete offense classification"""
    classification = get_object_or_404(OffenseClassification, pk=pk)
    
    if request.method == 'POST':
        classification.delete()
        messages.success(request, 'Offense classification deleted successfully.')
    else:
        classification.delete()
        messages.success(request, 'Offense classification deleted successfully.')
    return redirect('human_resource:violation_list')


# =============================================================================
# REMEDIAL ACTION VIEWS
# =============================================================================

@login_required
def remedial_action_list(request):
    """List all remedial actions"""
    range_filter = request.GET.get('range', '')
    
    actions = RemedialAction.objects.all()
    
    if range_filter:
        actions = actions.filter(range_code=range_filter)
    
    actions = actions.order_by('range_code', 'offense_count')
    
    return render(request, 'hr/default/compliance & offense management/settings/remedial_action_list.html', {
        'actions': actions,
        'range_filter': range_filter,
    })


@login_required
def remedial_action_add(request):
    """Add new remedial action"""
    if request.method == 'POST':
        range_code = request.POST.get('range_code')
        offense_count = request.POST.get('offense_count')
        action = request.POST.get('action')
        action_details = request.POST.get('action_details', '')
        is_active = request.POST.get('is_active') == 'on'
        
        if RemedialAction.objects.filter(range_code=range_code, offense_count=offense_count).exists():
            messages.error(request, 'This combination of range and offense count already exists.')
            return redirect('human_resource:violation_list')
        
        RemedialAction.objects.create(
            range_code=range_code,
            offense_count=offense_count,
            action=action,
            action_details=action_details,
            is_active=is_active,
        )
        messages.success(request, 'Remedial action created successfully.')
        return redirect('human_resource:violation_list')
    
    return render(request, 'hr/default/compliance & offense management/settings/remedial_action_form.html', {
        'action': 'Add',
    })


@login_required
def remedial_action_edit(request, pk):
    """Edit remedial action"""
    action = get_object_or_404(RemedialAction, pk=pk)
    
    if request.method == 'POST':
        action.action = request.POST.get('action')
        action.action_details = request.POST.get('action_details', '')
        action.is_active = request.POST.get('is_active') == 'on'
        action.save()
        
        messages.success(request, 'Remedial action updated successfully.')
        return redirect('human_resource:remedial_action_list')
    
    return render(request, 'hr/default/compliance & offense management/settings/remedial_action_form.html', {
        'action': 'Edit',
        'action_obj': action,
    })


@login_required
def remedial_action_delete(request, pk):
    """Delete remedial action"""
    action = get_object_or_404(RemedialAction, pk=pk)
    
    if request.method == 'POST':
        action.delete()
        messages.success(request, 'Remedial action deleted successfully.')
        return redirect('human_resource:remedial_action_list')
    
    return render(request, 'hr/default/compliance & offense management/settings/remedial_action_confirm_delete.html', {
        'action': action
    })


@login_required
def remedial_flowchart_partial(request):
    """Return the remedial action flowchart HTML via HTMX"""
    from django.http import JsonResponse
    
    # Get all remedial actions for the matrix
    actions = RemedialAction.objects.filter(is_active=True).order_by('range_code', 'offense_count')
    
    # Build the matrix data
    matrix = {
        'A': {1: None, 2: None, 3: None, 4: None, 5: None},
        'B': {1: None, 2: None, 3: None, 4: None, 5: None},
        'C': {1: None, 2: None, 3: None, 4: None, 5: None},
        'D': {1: None, 2: None, 3: None, 4: None, 5: None},
    }
    
    for action in actions:
        if action.range_code in matrix and 1 <= action.offense_count <= 5:
            matrix[action.range_code][action.offense_count] = action
    
    # Check if HTMX request
    if request.headers.get('HX-Request'):
        return render(request, 'hr/default/compliance & offense management/partials/remedial_flowchart.html', {
            'matrix': matrix
        })
    
    # Return JSON for debugging
    data = {}
    for range_code, actions_dict in matrix.items():
        data[range_code] = {}
        for count, action in actions_dict.items():
            if action:
                data[range_code][count] = {
                    'action': action.action,
                    'action_details': action.action_details,
                }
    return JsonResponse(data)


# =============================================================================
# VIOLATION CATEGORY VIEWS
# =============================================================================

@login_required
def violation_category_list(request):
    """List all violation categories"""
    categories = ViolationCategory.objects.all().order_by('display_order', 'name')
    return render(request, 'hr/default/compliance & offense management/settings/category_list.html', {
        'categories': categories,
    })


@login_required
def violation_category_add(request):
    """Add new violation category"""
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        display_order = request.POST.get('display_order', 0)
        is_active = request.POST.get('is_active') == 'on'
        
        ViolationCategory.objects.create(
            name=name,
            description=description,
            display_order=display_order,
            is_active=is_active,
        )
        messages.success(request, 'Violation category created successfully.')
        # Check if called from modal - if so, render with full context
        if request.headers.get('HX-Request'):
            # Need to include all context for the violation_list template
            categories = ViolationCategory.objects.filter(is_active=True).order_by('display_order', 'name')
            types = ViolationType.objects.filter(is_active=True).order_by('display_order', 'name')
            remedial_actions = RemedialAction.objects.filter(is_active=True).order_by('range_code', 'offense_count')
            offense_groups = OffenseGroup.objects.order_by('group_number')
            offense_sections = OffenseSection.objects.select_related('offense_group').order_by('offense_group', 'section_number')
            classifications = OffenseClassification.objects.select_related('offense_section').order_by('offense_section__offense_group', 'offense_section', 'id')[:50]
            employees = Staff.objects.all().order_by('last_name', 'first_name')
            
            return render(request, 'hr/default/compliance & offense management/violations/violation_list.html', {
                'categories': categories,
                'types': types,
                'remedial_actions': remedial_actions,
                'offense_groups': offense_groups,
                'offense_sections': offense_sections,
                'classifications': classifications,
                'employees': employees,
            })
        return redirect('human_resource:violation_list')
    
    return render(request, 'hr/default/compliance & offense management/settings/category_form.html', {
        'action': 'Add',
    })


@login_required
def violation_category_edit(request, pk):
    """Edit violation category"""
    category = get_object_or_404(ViolationCategory, pk=pk)
    
    if request.method == 'POST':
        category.name = request.POST.get('name')
        category.description = request.POST.get('description', '')
        category.display_order = request.POST.get('display_order', 0)
        category.is_active = request.POST.get('is_active') == 'on'
        category.save()
        
        messages.success(request, 'Violation category updated successfully.')
        return redirect('human_resource:violation_category_list')
    
    return render(request, 'hr/default/compliance & offense management/settings/category_form.html', {
        'action': 'Edit',
        'category': category,
    })


@login_required
def violation_category_delete(request, pk):
    """Delete violation category"""
    category = get_object_or_404(ViolationCategory, pk=pk)
    
    if request.method == 'POST':
        category.delete()
        messages.success(request, 'Violation category deleted successfully.')
        return redirect('human_resource:violation_category_list')
    
    return render(request, 'hr/default/compliance & offense management/settings/category_confirm_delete.html', {
        'category': category
    })


# =============================================================================
# VIOLATION TYPE VIEWS
# =============================================================================

@login_required
def violation_type_list(request):
    """List all violation types"""
    types = ViolationType.objects.all().order_by('display_order', 'name')
    return render(request, 'hr/default/compliance & offense management/settings/type_list.html', {
        'types': types,
    })


@login_required
def violation_type_add(request):
    """Add new violation type"""
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        display_order = request.POST.get('display_order', 0)
        is_active = request.POST.get('is_active') == 'on'
        
        ViolationType.objects.create(
            name=name,
            description=description,
            display_order=display_order,
            is_active=is_active,
        )
        messages.success(request, 'Violation type created successfully.')
        return redirect('human_resource:violation_list')
    
    return render(request, 'hr/default/compliance & offense management/settings/type_form.html', {
        'action': 'Add',
    })


@login_required
def violation_type_edit(request, pk):
    """Edit violation type"""
    vtype = get_object_or_404(ViolationType, pk=pk)
    
    if request.method == 'POST':
        vtype.name = request.POST.get('name')
        vtype.description = request.POST.get('description', '')
        vtype.display_order = request.POST.get('display_order', 0)
        vtype.is_active = request.POST.get('is_active') == 'on'
        vtype.save()
        
        messages.success(request, 'Violation type updated successfully.')
        return redirect('human_resource:violation_list')
    
    return render(request, 'hr/default/compliance & offense management/settings/type_form.html', {
        'action': 'Edit',
        'vtype': vtype,
    })


@login_required
def violation_type_delete(request, pk):
    """Delete violation type"""
    vtype = get_object_or_404(ViolationType, pk=pk)
    
    if request.method == 'POST':
        vtype.delete()
        messages.success(request, 'Violation type deleted successfully.')
        return redirect('human_resource:violation_type_list')
    
    return render(request, 'hr/default/compliance & offense management/settings/type_confirm_delete.html', {
        'vtype': vtype
    })


# =============================================================================
# EMPLOYEE VIOLATION VIEWS
# =============================================================================

@login_required
def violation_list(request):
    """List all employee violations with integrated settings - grouped by employee"""
    search = request.GET.get('search', '').strip()
    employee_filter = request.GET.get('employee', '')
    status_filter = request.GET.get('status', '')
    da_status_filter = request.GET.get('da_status', '')
    range_filter = request.GET.get('range', '')
    
    violations = EmployeeViolation.objects.select_related(
        'employee', 'category', 'violation_type', 'offense_classification', 'submitted_by'
    ).all()
    
    if search:
        violations = violations.filter(
            Q(employee__first_name__icontains=search) |
            Q(employee__last_name__icontains=search) |
            Q(type_of_incident__icontains=search)
        )
    
    if employee_filter:
        violations = violations.filter(employee_id=employee_filter)
    
    if status_filter:
        violations = violations.filter(status=status_filter)
    
    if da_status_filter:
        violations = violations.filter(da_status=da_status_filter)
    
    if range_filter:
        violations = violations.filter(remedial_action_range=range_filter)
    
    violations = violations.order_by('-created_at')
    
    # Group violations by employee
    employee_violations = {}
    for v in violations:
        emp_id = v.employee.id
        if emp_id not in employee_violations:
            employee_violations[emp_id] = {
                'employee': v.employee,
                'violations': [],
                'total': 0,
                'latest_status': None,
                'latest_range': None,
            }
        employee_violations[emp_id]['violations'].append(v)
        # Calculate total as sum of range values: A=1, B=2, C=3, D=4
        range_to_value = {'A': 1, 'B': 2, 'C': 3, 'D': 4}
        range_value = range_to_value.get(v.remedial_action_range, 0)
        employee_violations[emp_id]['total'] += range_value
        # Track latest (most recent based on created_at order)
        if employee_violations[emp_id]['latest_status'] is None:
            employee_violations[emp_id]['latest_status'] = v.status
            employee_violations[emp_id]['latest_range'] = v.remedial_action_range
    
    # Convert to list for pagination
    employee_list = list(employee_violations.values())
    
    # Sort by latest violation (most recent first)
    employee_list.sort(key=lambda x: x['violations'][0].created_at if x['violations'] else None, reverse=True)
    
    paginator = Paginator(employee_list, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    employees = Staff.objects.all().order_by('last_name', 'first_name')
    
    # Get settings data for the consolidated view
    categories = ViolationCategory.objects.filter(is_active=True).order_by('display_order', 'name')
    types = ViolationType.objects.filter(is_active=True).order_by('display_order', 'name')
    remedial_actions = RemedialAction.objects.filter(is_active=True).order_by('range_code', 'offense_count')
    
    # Get handbook data for quick reference
    offense_groups = OffenseGroup.objects.order_by('group_number')
    offense_sections = OffenseSection.objects.select_related('offense_group').order_by('offense_group', 'section_number')
    classifications = OffenseClassification.objects.select_related('offense_section').order_by('offense_section__offense_group', 'offense_section', 'id')[:50]
    
    # Get violation counts for stats
    pending_count = EmployeeViolation.objects.filter(status='working').count()
    resolved_count = EmployeeViolation.objects.filter(status='done').count()
    
    return render(request, 'hr/default/compliance & offense management/violations/violation_list.html', {
        'page_obj': page_obj,
        'search': search,
        'employee_filter': employee_filter,
        'status_filter': status_filter,
        'da_status_filter': da_status_filter,
        'range_filter': range_filter,
        'employees': employees,
        'categories': categories,
        'types': types,
        'remedial_actions': remedial_actions,
        'offense_groups': offense_groups,
        'offense_sections': offense_sections,
        'classifications': classifications,
        'pending_count': pending_count,
        'resolved_count': resolved_count,
    })


@login_required
def violation_detail(request, pk):
    """View violation details"""
    violation = get_object_or_404(EmployeeViolation, pk=pk)
    
    return render(request, 'hr/default/compliance & offense management/violations/violation_detail.html', {
        'violation': violation,
    })


@login_required
def violation_add(request):
    """Add new employee violation"""
    employees = Staff.objects.all().order_by('last_name', 'first_name')
    categories = ViolationCategory.objects.filter(is_active=True).order_by('display_order', 'name')
    types = ViolationType.objects.filter(is_active=True).order_by('display_order', 'name')
    
    if request.method == 'POST':
        employee_id = request.POST.get('employee')
        category_id = request.POST.get('category')
        violation_type_id = request.POST.get('violation_type')
        date_submitted = request.POST.get('date_submitted')
        type_of_incident = request.POST.get('type_of_incident')
        hr_note = request.POST.get('hr_note', '')
        offense_classification_id = request.POST.get('offense_classification')
        da_status = request.POST.get('da_status', 'working')
        fully_signed = request.POST.get('fully_signed') == 'on'
        decision = request.POST.get('decision', '')
        status = request.POST.get('status', 'working')
        
        employee = get_object_or_404(Staff, pk=employee_id)
        
        # Get the current user from session as submitted_by
        submitted_by = None
        emp_num = request.session.get('employee_number')
        if emp_num:
            submitted_by = Staff.objects.filter(employee_number=emp_num).first()
        
        violation = EmployeeViolation(
            employee=employee,
            category_id=category_id if category_id else None,
            violation_type_id=violation_type_id if violation_type_id else None,
            date_submitted=date_submitted,
            type_of_incident=type_of_incident,
            hr_note=hr_note,
            offense_classification_id=offense_classification_id if offense_classification_id else None,
            da_status=da_status,
            fully_signed=fully_signed,
            decision=decision,
            submitted_by=submitted_by,
            status=status,
        )
        violation.save()
        
        messages.success(request, 'Employee violation created successfully.')
        return redirect('human_resource:violation_list')
    
    return render(request, 'hr/default/compliance & offense management/violations/violation_form.html', {
        'action': 'Add',
        'employees': employees,
        'categories': categories,
        'types': types,
        'violation': None,
    })


@login_required
def violation_edit(request, pk):
    """Edit employee violation"""
    violation = get_object_or_404(EmployeeViolation, pk=pk)
    employees = Staff.objects.all().order_by('last_name', 'first_name')
    categories = ViolationCategory.objects.filter(is_active=True).order_by('display_order', 'name')
    types = ViolationType.objects.filter(is_active=True).order_by('display_order', 'name')
    
    if request.method == 'POST':
        violation.category_id = request.POST.get('category') or None
        violation.violation_type_id = request.POST.get('violation_type') or None
        violation.status = request.POST.get('status', 'working')
        violation.date_submitted = request.POST.get('date_submitted')
        violation.type_of_incident = request.POST.get('type_of_incident')
        violation.hr_note = request.POST.get('hr_note', '')
        violation.offense_classification_id = request.POST.get('offense_classification') or None
        violation.da_status = request.POST.get('da_status', 'working')
        violation.fully_signed = request.POST.get('fully_signed') == 'on'
        violation.decision = request.POST.get('decision', '')
        violation.save()
        
        messages.success(request, 'Employee violation updated successfully.')
        return redirect('human_resource:violation_list')
    
    return render(request, 'hr/default/compliance & offense management/violations/violation_form.html', {
        'action': 'Edit',
        'violation': violation,
        'employees': employees,
        'categories': categories,
        'types': types,
    })


@login_required
def violation_delete(request, pk):
    """Delete employee violation"""
    violation = get_object_or_404(EmployeeViolation, pk=pk)
    
    if request.method == 'POST':
        violation.delete()
        messages.success(request, 'Employee violation deleted successfully.')
        return redirect('human_resource:violation_list')
    
    return render(request, 'hr/default/compliance & offense management/violations/violation_confirm_delete.html', {
        'violation': violation
    })


# =============================================================================
# AJAX VIEWS
# =============================================================================

@login_required
def ajax_classifications(request):
    """Get classifications for modal selector"""
    group_id = request.GET.get('group_id')
    section_id = request.GET.get('section_id')
    
    classifications = OffenseClassification.objects.filter(is_active=True)
    
    if group_id:
        classifications = classifications.filter(offense_section__offense_group_id=group_id)
    
    if section_id:
        classifications = classifications.filter(offense_section_id=section_id)
    
    classifications = classifications.select_related(
        'offense_section__offense_group'
    ).order_by('offense_section', 'id')
    
    data = []
    for c in classifications:
        data.append({
            'id': c.id,
            'description': c.offense_description,
            'section': f"{c.offense_section.section_number}: {c.offense_section.section_title}",
            'group': f"{c.offense_section.offense_group.group_number}: {c.offense_section.offense_group.group_name}",
            'default_range': c.default_range,
        })
    
    return JsonResponse({'classifications': data})


@login_required
def ajax_get_employee_violations(request):
    """Get violations for a specific employee (for modal)"""
    employee_id = request.GET.get('employee_id')
    
    violations = EmployeeViolation.objects.filter(
        employee_id=employee_id
    ).select_related(
        'offense_classification'
    ).order_by('-created_at')
    
    data = []
    for v in violations:
        data.append({
            'id': v.id,
            'incident_number': v.incident_number,
            'incident_label': v.incident_label,
            'status': v.get_status_display(),
            'range': v.remedial_action_range,
            'action': v.remedial_action.action if v.remedial_action else None,
            'date_submitted': str(v.date_submitted),
        })
    
    return JsonResponse({'violations': data, 'count': violations.count()})

@login_required
def ajax_violation_filter(request):
    """AJAX filter endpoint returning HTML table content"""
    search = request.GET.get('search', '').strip()
    employee_filter = request.GET.get('employee', '')
    status_filter = request.GET.get('status', '')
    da_status_filter = request.GET.get('da_status', '')
    range_filter = request.GET.get('range', '')
    page_number = request.GET.get('page', 1)
    
    violations = EmployeeViolation.objects.select_related(
        'employee', 'category', 'violation_type', 'offense_classification', 'submitted_by', 'remedial_action'
    ).all()
    
    if search:
        violations = violations.filter(
            Q(employee__first_name__icontains=search) |
            Q(employee__last_name__icontains=search) |
            Q(type_of_incident__icontains=search)
        )
    
    if employee_filter:
        violations = violations.filter(employee_id=employee_filter)
    if status_filter:
        violations = violations.filter(status=status_filter)
    if da_status_filter:
        violations = violations.filter(da_status=da_status_filter)
    if range_filter:
        violations = violations.filter(remedial_action_range=range_filter)
    
    violations = violations.order_by('-created_at')
    
    # Group by employee
    employee_violations = {}
    for v in violations:
        emp_id = v.employee.id
        if emp_id not in employee_violations:
            employee_violations[emp_id] = {
                'employee': v.employee,
                'violations': [],
                'total': 0,
                'latest_status': None,
                'latest_range': None,
            }
        employee_violations[emp_id]['violations'].append(v)
        range_to_value = {'A': 1, 'B': 2, 'C': 3, 'D': 4}
        range_value = range_to_value.get(v.remedial_action_range, 0)
        employee_violations[emp_id]['total'] += range_value
        if employee_violations[emp_id]['latest_status'] is None:
            employee_violations[emp_id]['latest_status'] = v.status
            employee_violations[emp_id]['latest_range'] = v.remedial_action_range
    
    employee_list = list(employee_violations.values())
    employee_list.sort(key=lambda x: x['violations'][0].created_at if x['violations'] else None, reverse=True)
    
    paginator = Paginator(employee_list, 20)
    page_obj = paginator.get_page(page_number)
    
    # Get employees list for filter dropdown
    employees = Staff.objects.all().order_by('last_name', 'first_name')
    categories = ViolationCategory.objects.filter(is_active=True).order_by('display_order', 'name')
    types = ViolationType.objects.filter(is_active=True).order_by('display_order', 'name')
    
    # Render only the table body and pagination using a partial template
    # For simplicity, we'll return rendered HTML strings
    from django.template.loader import render_to_string
    
    html_content = render_to_string('hr/default/compliance & offense management/violations/violation_table_body.html', {
        'page_obj': page_obj,
        'search': search,
        'employee_filter': employee_filter,
        'status_filter': status_filter,
        'da_status_filter': da_status_filter,
        'range_filter': range_filter,
        'employees': employees,
    }, request=request)
    
    return JsonResponse({
        'html': html_content,
        'has_other_pages': page_obj.has_other_pages(),
        'start_index': page_obj.start_index(),
        'end_index': page_obj.end_index(),
        'total': page_obj.paginator.count,
    })


@login_required
def ajax_violation_detail(request, pk):
    """Get violation details for modal popup"""
    violation = get_object_or_404(EmployeeViolation, pk=pk)
    
    data = {
        'id': violation.id,
        'incident_label': violation.incident_label,
        'employee': f"{violation.employee.first_name} {violation.employee.last_name}",
        'category': violation.category.name if violation.category else '-',
        'violation_type': violation.violation_type.name if violation.violation_type else '-',
        'date_submitted': str(violation.date_submitted),
        'remedial_action_range': violation.remedial_action_range,
        'action': violation.remedial_action.action if violation.remedial_action else '-',
        'offense_count': violation.offense_count,
        'classification': violation.offense_classification.offense_description if violation.offense_classification else '-',
        'type_of_incident': violation.type_of_incident,
        'hr_note': violation.hr_note or '',
        'da_status': violation.get_da_status_display(),
        'decision': violation.get_decision_display() if violation.decision else '-',
        'fully_signed': violation.fully_signed,
        'status': violation.get_status_display(),
        'submitted_by': f"{violation.submitted_by.first_name} {violation.submitted_by.last_name}" if violation.submitted_by else '-',
    }
    
    return JsonResponse(data)


@login_required
def ajax_update_violation_status(request, pk):
    """Update violation status via AJAX"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method allowed'}, status=405)
    
    violation = get_object_or_404(EmployeeViolation, pk=pk)
    new_status = request.POST.get('status')
    
    if new_status not in ['done', 'working', 'stuck']:
        return JsonResponse({'error': 'Invalid status'}, status=400)
    
    violation.status = new_status
    violation.save()
    
    return JsonResponse({
        'success': True,
        'id': violation.id,
        'status': violation.get_status_display(),
    })


@login_required
def ajax_update_violation_da_status(request, pk):
    """Update violation DA status via AJAX"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method allowed'}, status=405)
    
    violation = get_object_or_404(EmployeeViolation, pk=pk)
    new_da_status = request.POST.get('da_status')
    
    if new_da_status not in ['done', 'working', 'stuck']:
        return JsonResponse({'error': 'Invalid DA status'}, status=400)
    
    violation.da_status = new_da_status
    violation.save()
    
    return JsonResponse({
        'success': True,
        'id': violation.id,
        'da_status': violation.get_da_status_display(),
    })