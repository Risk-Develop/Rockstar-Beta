"""
ENPS (Employee Net Promoter Score) Survey Views
================================================
- Survey management for HR admins
- Employee-facing survey form
- Analytics dashboard with department analysis, trends, and heatmap
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.template.loader import render_to_string
from django.utils import timezone
from django.db.models import Count, Avg, Q
from django.core.paginator import Paginator
from django.contrib import messages
from datetime import datetime, date
import json

from .models import ENPSSurvey, ENPSResponse, ENPSDepartmentAnalytics, ENPSSurveyQuestion, ENPSQuestionResponse
from App.users.models import Staff


# ═══════════════════════════════════════════════════════════════════════════════
# HR Admin Views - Survey Management
# ═══════════════════════════════════════════════════════════════════════════════

def enps_survey_list(request):
    """List all ENPS surveys"""
    from django.db.models import Count
    from django.db.models import Avg
    
    # Use annotation to get question count and response count efficiently
    surveys = ENPSSurvey.objects.annotate(
        question_count=Count('questions', distinct=True),
        annotated_response_count=Count('responses', distinct=True)
    ).prefetch_related('questions').all()
    
    # Add computed field for dynamic score based on question type
    for survey in surveys:
        questions = survey.questions.all().order_by('order')
        
        # Get first question of each type
        first_nps_q = questions.filter(question_type='nps').first()
        first_rating5_q = questions.filter(question_type='rating_5').first()
        first_rating3_q = questions.filter(question_type='rating_3').first()
        first_yesno_q = questions.filter(question_type='yes_no').first()
        
        # Calculate score based on first available question type
        survey.question_type_display = 'nps'  # Default
        survey.enps_score_val = 0
        survey.avg_score_display = None
        
        # Use question responses if available, otherwise use response scores
        if first_nps_q:
            survey.question_type_display = 'nps'
            q_responses = ENPSQuestionResponse.objects.filter(question=first_nps_q)
            total = q_responses.count()
            if total > 0:
                promoters = q_responses.filter(score_value__gte=9).count()
                detractors = q_responses.filter(score_value__lte=6).count()
                survey.enps_score_val = round(((promoters - detractors) / total) * 100, 1)
                survey.avg_score_display = round(q_responses.aggregate(Avg('score_value'))['score_value__avg'] or 0, 1)
        elif first_rating5_q:
            survey.question_type_display = 'rating_5'
            q_responses = ENPSQuestionResponse.objects.filter(question=first_rating5_q)
            total = q_responses.count()
            if total > 0:
                survey.enps_score_val = round(q_responses.aggregate(Avg('score_value'))['score_value__avg'] or 0, 1)
                survey.avg_score_display = survey.enps_score_val
        elif first_rating3_q:
            survey.question_type_display = 'rating_3'
            q_responses = ENPSQuestionResponse.objects.filter(question=first_rating3_q)
            total = q_responses.count()
            if total > 0:
                survey.enps_score_val = round(q_responses.aggregate(Avg('score_value'))['score_value__avg'] or 0, 1)
                survey.avg_score_display = survey.enps_score_val
        elif first_yesno_q:
            survey.question_type_display = 'yes_no'
            q_responses = ENPSQuestionResponse.objects.filter(question=first_yesno_q)
            total = q_responses.count()
            if total > 0:
                yes_count = q_responses.filter(boolean_value=True).count()
                survey.enps_score_val = round((yes_count / total) * 100, 1)  # Yes percentage
                survey.avg_score_display = f"{survey.enps_score_val}%"
        else:
            # Fallback to old method (based on ENPSResponse model)
            survey.enps_score_val = survey.enps_score
    
    # Calculate stats for dashboard cards
    active_count = surveys.filter(is_active=True).count()
    total_responses = sum(survey.annotated_response_count for survey in surveys)
    
    # Calculate average ENPS score
    scores_with_responses = [s.enps_score_val for s in surveys if s.annotated_response_count > 0]
    avg_enps = sum(scores_with_responses) / len(scores_with_responses) if scores_with_responses else 0
    
    context = {
        'surveys': surveys,
        'page_title': 'ENPS Surveys',
        'active_count': active_count,
        'total_responses': total_responses,
        'avg_enps': round(avg_enps, 1),
    }
    return render(request, 'hr/default/survey/enps/survey_list.html', context)


def enps_survey_create(request):
    """Create a new ENPS survey"""
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date') or None
        allow_anonymous = request.POST.get('allow_anonymous') == 'on'
        
        survey = ENPSSurvey.objects.create(
            name=name,
            description=description,
            start_date=start_date,
            end_date=end_date,
            allow_anonymous=allow_anonymous,
            is_active=True
        )
        
        # Process and save new questions
        _save_survey_questions(request.POST, survey, is_new=True)
        
        messages.success(request, f'Survey "{survey.name}" created successfully!')
        return redirect('human_resource:enps_survey_list')
    
    context = {
        'page_title': 'Create ENPS Survey',
    }
    return render(request, 'hr/default/survey/enps/survey_form.html', context)


def _save_survey_questions(post_data, survey, is_new=False):
    """
    Helper function to save/update survey questions.
    
    Args:
        post_data: The POST data from the form
        survey: The ENPSSurvey instance
        is_new: If True, this is a new survey (no existing questions to update)
    """
    # Get existing question IDs from the form (for edit mode)
    existing_question_ids = []
    if not is_new:
        for key in post_data:
            if key.startswith('question_id_'):
                q_id = key.replace('question_id_', '')
                existing_question_ids.append(int(q_id))
        
        # Delete questions that were removed in the form
        survey.questions.exclude(id__in=existing_question_ids).delete()
    
    # Process existing questions (for edit mode)
    if not is_new:
        for key in post_data:
            if key.startswith('question_text_'):
                q_id = key.replace('question_text_', '')
                if q_id.isdigit():
                    question_text = post_data.get(key, '').strip()
                    if question_text:
                        question_type = post_data.get(f'question_type_{q_id}', 'nps')
                        is_required = post_data.get(f'question_required_{q_id}') == 'on'
                        order = int(post_data.get(f'question_order_{q_id}', 0))
                        
                        ENPSSurveyQuestion.objects.update_or_create(
                            id=int(q_id),
                            survey=survey,
                            defaults={
                                'question_text': question_text,
                                'question_type': question_type,
                                'is_required': is_required,
                                'order': order,
                            }
                        )
    
    # Process new questions (question_text_new_0, question_text_new_1, etc.)
    new_question_indices = []
    for key in post_data:
        if key.startswith('question_text_new_'):
            index = key.replace('question_text_new_', '')
            new_question_indices.append(index)
    
    # Sort indices to maintain order
    new_question_indices.sort()
    
    for index in new_question_indices:
        question_text = post_data.get(f'question_text_new_{index}', '').strip()
        if question_text:
            question_type = post_data.get(f'question_type_new_{index}', 'nps')
            is_required = post_data.get(f'question_required_new_{index}') == 'on'
            
            # Calculate order - new questions go after existing ones
            order = len(existing_question_ids) + new_question_indices.index(index)
            
            ENPSSurveyQuestion.objects.create(
                survey=survey,
                question_text=question_text,
                question_type=question_type,
                is_required=is_required,
                order=order,
            )


def enps_survey_detail(request, survey_id):
    """View survey details and responses"""
    survey = get_object_or_404(ENPSSurvey, id=survey_id)
    responses = survey.responses.select_related('employee').prefetch_related('question_responses__question').all()
    
    # Get filter parameters
    department_filter = request.GET.get('department', '')
    category_filter = request.GET.get('category', '')
    date_start = request.GET.get('date_start', '')
    date_end = request.GET.get('date_end', '')
    date_filter = request.GET.get('date_filter', '')
    search_query = request.GET.get('search', '')
    
    # Apply date_filter label-based filtering (takes precedence over manual date range)
    from datetime import datetime, timedelta
    from django.utils import timezone
    today = timezone.now().date()
    
    if date_filter and not date_start and not date_end:
        if date_filter == 'today':
            date_start = today.strftime('%Y-%m-%d')
            date_end = today.strftime('%Y-%m-%d')
        elif date_filter == 'yesterday':
            yesterday = today - timedelta(days=1)
            date_start = yesterday.strftime('%Y-%m-%d')
            date_end = yesterday.strftime('%Y-%m-%d')
        elif date_filter == 'last_7_days':
            date_start = (today - timedelta(days=6)).strftime('%Y-%m-%d')
            date_end = today.strftime('%Y-%m-%d')
        elif date_filter == 'last_30_days':
            date_start = (today - timedelta(days=29)).strftime('%Y-%m-%d')
            date_end = today.strftime('%Y-%m-%d')
        elif date_filter == 'this_month':
            # First day of current month
            date_start = today.replace(day=1).strftime('%Y-%m-%d')
            date_end = today.strftime('%Y-%m-%d')
        elif date_filter == 'this_quarter':
            # Calculate quarter start month
            current_month = today.month
            quarter_start_month = ((current_month - 1) // 3) * 3 + 1
            date_start = today.replace(month=quarter_start_month, day=1).strftime('%Y-%m-%d')
            date_end = today.strftime('%Y-%m-%d')
    
    # Apply filters
    if department_filter:
        responses = responses.filter(department__icontains=department_filter)
    if category_filter:
        responses = responses.filter(category=category_filter)
    if date_start:
        try:
            from datetime import datetime
            start_date = datetime.strptime(date_start, '%Y-%m-%d')
            responses = responses.filter(created_at__gte=start_date)
        except ValueError:
            pass
    if date_end:
        try:
            from datetime import datetime
            end_date = datetime.strptime(date_end, '%Y-%m-%d')
            from datetime import timedelta
            end_date = end_date + timedelta(days=1)
            responses = responses.filter(created_at__lt=end_date)
        except ValueError:
            pass
    if search_query:
        responses = responses.filter(
            Q(employee__employee_number__icontains=search_query) |
            Q(employee__first_name__icontains=search_query) |
            Q(employee__last_name__icontains=search_query)
        )
    
    # Get all unique departments from responses for the filter dropdown
    all_departments = sorted(list(responses.values_list('department', flat=True).distinct()))
    all_departments = [d for d in all_departments if d]  # Remove None/empty
    
    # Get all unique categories from responses for the filter dropdown
    all_categories = sorted(list(responses.values_list('category', flat=True).distinct()))
    all_categories = [c for c in all_categories if c]
    
    # Order after filtering
    responses = responses.order_by('-created_at')
    
    # Pagination
    paginator = Paginator(responses, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Summary stats
    total_responses = responses.count()
    enps_score = 0  # Will be calculated based on question types below
    
    # Calculate participation rate (count all staff)
    total_employees = Staff.objects.count()
    participation_rate = 0
    if total_employees > 0:
        participation_rate = round((total_responses / total_employees) * 100, 1)
    
    # =========================================================================
    # DYNAMIC MAIN STATS - Based on question types from survey form
    # =========================================================================
    questions = survey.questions.all().prefetch_related('responses').order_by('order')
    
    # Get response IDs from filtered responses FIRST (before calculating stats)
    response_ids = set(responses.values_list('id', flat=True))
    
    # Add response count and average score to each question (using filtered responses)
    question_stats = []
    total_score_sum = 0
    total_score_count = 0
    
    for q in questions:
        # Use ENPSQuestionResponse to get actual responses to this question (filtered)
        from django.db.models import Avg
        q_responses = ENPSQuestionResponse.objects.filter(question=q, response_id__in=response_ids)
        resp_count = q_responses.count()
        avg_score = None
        max_score = None
        
        if resp_count > 0:
            if q.question_type == 'nps':
                avg_score = q_responses.aggregate(Avg('score_value'))['score_value__avg']
                if avg_score is not None:
                    avg_score = round(avg_score, 2)
                    total_score_sum += avg_score
                    total_score_count += 1
                max_score = 10
            elif q.question_type == 'rating_5':
                avg_score = q_responses.aggregate(Avg('score_value'))['score_value__avg']
                if avg_score is not None:
                    avg_score = round(avg_score, 2)
                    # Convert to 0-10 scale for combined
                    total_score_sum += avg_score * 2
                    total_score_count += 1
                max_score = 5
            elif q.question_type == 'rating_3':
                avg_score = q_responses.aggregate(Avg('score_value'))['score_value__avg']
                if avg_score is not None:
                    avg_score = round(avg_score, 2)
                    # Convert to 0-10 scale for combined
                    total_score_sum += avg_score * (10/3)
                    total_score_count += 1
                max_score = 3
            elif q.question_type == 'yes_no':
                yes_count = q_responses.filter(boolean_value=True).count()
                avg_score = round((yes_count / resp_count) * 100, 1)  # Yes percentage
                max_score = 100
        
        question_stats.append({
            'question': q,
            'response_count': resp_count,
            'avg_score': avg_score,
            'max_score': max_score,
        })
    
    # Calculate combined average (normalized to 0-10 scale) - now uses filtered data
    combined_avg = None
    if total_score_count > 0:
        combined_avg = round(total_score_sum / total_score_count, 2)
    
    # Initialize dynamic stats
    promoter_count = 0
    passive_count = 0
    detractor_count = 0
    
    main_question_type = None
    main_question_text = None
    main_avg_score = None
    main_enps_score = None
    main_yes_count = None
    main_no_count = None
    main_yes_pct = None
    main_no_pct = None
    main_rating_dist = []
    main_text_response_count = None
    
    # Get first question of each type
    first_nps_q = questions.filter(question_type='nps').first()
    first_rating5_q = questions.filter(question_type='rating_5').first()
    first_rating3_q = questions.filter(question_type='rating_3').first()
    first_yesno_q = questions.filter(question_type='yes_no').first()
    first_text_q = questions.filter(question_type='text').first()
    
    # Calculate stats based on first NPS question
    if first_nps_q:
        main_question_type = 'nps'
        main_question_text = first_nps_q.question_text
        # Filter to only include responses that are in our filtered set
        nps_responses = ENPSQuestionResponse.objects.filter(question=first_nps_q, response_id__in=response_ids)
        nps_total = nps_responses.count()
        if nps_total > 0:
            main_avg_score = round(nps_responses.aggregate(Avg('score_value'))['score_value__avg'] or 0, 1)
            nps_promoters = nps_responses.filter(score_value__gte=9).count()
            nps_passives = nps_responses.filter(score_value__gte=7, score_value__lte=8).count()
            nps_detractors = nps_responses.filter(score_value__lte=6).count()
            main_enps_score = round(((nps_promoters - nps_detractors) / nps_total) * 100, 1)
            total_responses = nps_total
            enps_score = main_enps_score
            
            # Add to context for breakdown display
            promoter_count = nps_promoters
            passive_count = nps_passives
            detractor_count = nps_detractors
        else:
            # No responses yet, reset to 0 instead of using legacy value
            main_avg_score = 0
            main_enps_score = 0
            enps_score = 0
            total_responses = 0
    
    # Calculate stats based on first 5-star rating question
    elif first_rating5_q:
        main_question_type = 'rating_5'
        main_question_text = first_rating5_q.question_text
        rating_responses = ENPSQuestionResponse.objects.filter(question=first_rating5_q, response_id__in=response_ids)
        rating_total = rating_responses.count()
        if rating_total > 0:
            main_avg_score = round(rating_responses.aggregate(Avg('score_value'))['score_value__avg'] or 0, 1)
            main_rating_dist = []
            for i in range(5, 0, -1):
                count = rating_responses.filter(score_value=i).count()
                pct = round((count / rating_total) * 100, 1) if rating_total > 0 else 0
                main_rating_dist.append({'stars': i, 'count': count, 'pct': pct})
            total_responses = rating_total
            # For rating_5, show average score as the main score
            enps_score = main_avg_score
    
    # Calculate stats based on first 3-star rating question
    elif first_rating3_q:
        main_question_type = 'rating_3'
        main_question_text = first_rating3_q.question_text
        rating_responses = ENPSQuestionResponse.objects.filter(question=first_rating3_q, response_id__in=response_ids)
        rating_total = rating_responses.count()
        if rating_total > 0:
            main_avg_score = round(rating_responses.aggregate(Avg('score_value'))['score_value__avg'] or 0, 1)
            main_rating_dist = []
            for i in range(3, 0, -1):
                count = rating_responses.filter(score_value=i).count()
                pct = round((count / rating_total) * 100, 1) if rating_total > 0 else 0
                main_rating_dist.append({'stars': i, 'count': count, 'pct': pct})
            total_responses = rating_total
            # For rating_3, show average score as the main score
            enps_score = main_avg_score
    
    # Calculate stats based on first Yes/No question
    elif first_yesno_q:
        main_question_type = 'yes_no'
        main_question_text = first_yesno_q.question_text
        yesno_responses = ENPSQuestionResponse.objects.filter(question=first_yesno_q, response_id__in=response_ids)
        yesno_total = yesno_responses.count()
        if yesno_total > 0:
            main_yes_count = yesno_responses.filter(boolean_value=True).count()
            main_no_count = yesno_responses.filter(boolean_value=False).count()
            main_yes_pct = round((main_yes_count / yesno_total) * 100, 1)
            main_no_pct = round((main_no_count / yesno_total) * 100, 1)
            total_responses = yesno_total
            # For yes_no, show yes percentage as the main score
            enps_score = main_yes_pct
    
    # Calculate stats based on first Text question
    elif first_text_q:
        main_question_type = 'text'
        main_question_text = first_text_q.question_text
        text_responses = ENPSQuestionResponse.objects.filter(question=first_text_q, response_id__in=response_ids)
        main_text_response_count = text_responses.count()
        total_responses = main_text_response_count
    
    # Category breakdown
    category_stats = responses.values('category').annotate(count=Count('id'))
    category_dict = {item['category']: item['count'] for item in category_stats}
    
    # Score distribution
    score_distribution = []
    for i in range(11):
        count = responses.filter(score=i).count()
        score_distribution.append({'score': i, 'count': count})
    
    # =========================================================================
    # Department-level Summary (NEW TABLE)
    # =========================================================================
    
    # Get active employees by department - use departmentlink (ForeignKey) for proper matching
    active_employees_by_dept = {}
    for staff in Staff.objects.filter(status='active'):
        if staff.departmentlink:
            # Use departmentlink (ForeignKey) to get the department name
            dept_name = staff.departmentlink.department_name
            active_employees_by_dept[dept_name] = active_employees_by_dept.get(dept_name, 0) + 1
    
    # Calculate stats per department
    department_stats = []
    
    # Get all departments from filtered responses
    dept_response_groups = responses.exclude(department__isnull=True).exclude(department='').values('department').annotate(
        response_count=Count('id'),
        avg_score=Avg('score')
    )
    
    for dept_data in dept_response_groups:
        dept_name = dept_data['department']
        respondent_count = dept_data['response_count']
        
        # Get expected (active employees in this department)
        expected_count = active_employees_by_dept.get(dept_name, 0)
        
        # Calculate response rate
        response_rate = round((respondent_count / expected_count * 100), 1) if expected_count > 0 else 0
        
        # Calculate eNPS for this department (using question responses)
        if first_nps_q and respondent_count > 0:
            # Get NPS responses for this department
            dept_response_ids = responses.filter(department=dept_name).values_list('id', flat=True)
            dept_nps_responses = ENPSQuestionResponse.objects.filter(
                question=first_nps_q, 
                response_id__in=dept_response_ids
            )
            nps_total = dept_nps_responses.count()
            if nps_total > 0:
                nps_promoters = dept_nps_responses.filter(score_value__gte=9).count()
                nps_detractors = dept_nps_responses.filter(score_value__lte=6).count()
                dept_enps = round(((nps_promoters - nps_detractors) / nps_total) * 100, 1)
            else:
                dept_enps = 0
        else:
            # Use overall score for non-NPS surveys
            dept_enps = dept_data['avg_score'] if dept_data['avg_score'] else 0
        
        # Satisfaction is the average score
        satisfaction = round(dept_data['avg_score'], 1) if dept_data['avg_score'] else 0
        
        department_stats.append({
            'department': dept_name,
            'respondents': respondent_count,
            'expected': expected_count,
            'response_rate': response_rate,
            'satisfaction': satisfaction,
            'enps': dept_enps,
        })
    
    # Sort by department name
    department_stats = sorted(department_stats, key=lambda x: x['department'])
    
    # Check if this is an HTMX request
    is_htmx = request.headers.get('HX-Request', False)
    
    # For HTMX requests, return comprehensive partial with all sections
    if is_htmx:
        context = {
            'survey': survey,
            'page_obj': page_obj,
            'allow_anonymous': survey.allow_anonymous,
            'main_question_type': main_question_type,
            'all_departments': all_departments,
            'all_categories': all_categories,
            'current_department': department_filter,
            'current_category': category_filter,
            'current_date_start': date_start,
            'current_date_end': date_end,
            'current_date_filter': date_filter,
            'current_search': search_query,
            'promoter_count': promoter_count,
            'passive_count': passive_count,
            'detractor_count': detractor_count,
            'total_responses': total_responses,
            'enps_score': enps_score,
            'avg_score': main_avg_score,
            'participation_rate': participation_rate,
            'question_stats': question_stats,
            'combined_avg': combined_avg,
            'main_avg_score': main_avg_score,
            'department_stats': department_stats,
            'is_htmx': True,
        }
        return render(request, 'hr/default/survey/enps/_survey_content_partial.html', context)
    
    context = {
        'survey': survey,
        'page_obj': page_obj,
        'total_responses': total_responses,
        'enps_score': enps_score,
        'participation_rate': participation_rate,
        'avg_score': main_avg_score,
        'category_dict': category_dict,
        'score_distribution': score_distribution,
        'page_title': f'Survey: {survey.name}',
        # Anonymous flag
        'allow_anonymous': survey.allow_anonymous,
        # Dynamic main stats based on question type
        'main_question_type': main_question_type,
        'main_question_text': main_question_text,
        'main_rating_dist': main_rating_dist,
        'main_yes_count': main_yes_count,
        'main_no_count': main_no_count,
        'main_yes_pct': main_yes_pct,
        'main_no_pct': main_no_pct,
        'main_text_response_count': main_text_response_count,
        # Pass questions for dynamic cards
        'questions': questions,
        'question_stats': question_stats,
        'combined_avg': combined_avg,
        'department_stats': department_stats,
        # Filter options
        'all_departments': all_departments,
        'all_categories': all_categories,
        'current_department': department_filter,
        'current_category': category_filter,
        'current_date_start': date_start,
        'current_date_end': date_end,
        'current_date_filter': date_filter,
        'current_search': search_query,
        # Response breakdown counts
        'promoter_count': promoter_count,
        'passive_count': passive_count,
        'detractor_count': detractor_count,
        # HTMX flag
        'is_htmx': is_htmx,
    }
    return render(request, 'hr/default/survey/enps/survey_detail.html', context)


def enps_survey_edit(request, survey_id):
    """Edit an existing survey"""
    survey = get_object_or_404(ENPSSurvey, id=survey_id)
    
    if request.method == 'POST':
        survey.name = request.POST.get('name')
        survey.description = request.POST.get('description', '')
        survey.start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        survey.end_date = end_date if end_date else None
        survey.allow_anonymous = request.POST.get('allow_anonymous') == 'on'
        survey.is_active = request.POST.get('is_active') == 'on'
        survey.save()
        
        # Process and save questions (updates existing, adds new, deletes removed)
        _save_survey_questions(request.POST, survey, is_new=False)
        
        messages.success(request, f'Survey "{survey.name}" updated successfully!')
        return redirect('human_resource:enps_survey_list')
    
    context = {
        'survey': survey,
        'page_title': f'Edit: {survey.name}',
    }
    return render(request, 'hr/default/survey/enps/survey_form.html', context)


def enps_survey_delete(request, survey_id):
    """Delete a survey"""
    survey = get_object_or_404(ENPSSurvey, id=survey_id)
    
    if request.method == 'POST':
        survey.delete()
        return redirect('human_resource:enps_survey_list')
    
    context = {
        'survey': survey,
        'page_title': f'Delete: {survey.name}',
    }
    return render(request, 'hr/default/survey/enps/survey_confirm_delete.html', context)


# ═══════════════════════════════════════════════════════════════════════════════
# Analytics Dashboard
# ═══════════════════════════════════════════════════════════════════════════════

def enps_analytics(request, survey_id):
    """Main analytics dashboard"""
    survey = get_object_or_404(ENPSSurvey, id=survey_id)
    responses = survey.responses.all()
    
    # Overall stats - calculate from question responses for accuracy
    questions = survey.questions.all().order_by('order')
    
    # Check if survey has questions
    if not questions.exists():
        # No questions configured - show empty state
        context = {
            'survey': survey,
            'questions': questions,
            'question_analytics': [],
            'total_responses': 0,
            'enps_score': 0,
            'raw_enps_score': 0,
            'display_score': 0,
            'promoters': 0,
            'promoters_pct': 0,
            'passives': 0,
            'passives_pct': 0,
            'detractors': 0,
            'detractors_pct': 0,
            'avg_score': 0,
            'department_stats': [],
            'score_distribution': [0] * 11,
            'emoji_stats': [],
            'all_departments': [],
            'page_title': f'Analytics: {survey.name}',
            'main_question_type': None,
            'main_question_text': None,
            'main_rating_dist': [],
            'main_yes_count': 0,
            'main_no_count': 0,
            'main_yes_pct': 0,
            'main_no_pct': 0,
            'no_questions': True,
        }
        return render(request, 'hr/default/survey/enps/analytics.html', context)
    
    # Get first question of each type
    first_nps_q = questions.filter(question_type='nps').first()
    first_rating5_q = questions.filter(question_type='rating_5').first()
    first_rating3_q = questions.filter(question_type='rating_3').first()
    first_yesno_q = questions.filter(question_type='yes_no').first()
    
    # Calculate stats based on first available question type
    total_responses = 0
    enps_score = 0
    promoters = 0
    passives = 0
    detractors = 0
    promoters_pct = 0
    passives_pct = 0
    detractors_pct = 0
    avg_score = 0
    main_question_type = None
    main_question_text = None
    main_enps_score = None
    main_avg_score = None
    main_yes_count = 0
    main_no_count = 0
    main_yes_pct = 0
    main_no_pct = 0
    main_rating_dist = []
    
    # Get total responses from ENPSResponse (base response count)
    total_responses = responses.count()
    
    if first_nps_q:
        main_question_type = 'nps'
        main_question_text = first_nps_q.question_text
        nps_responses = ENPSQuestionResponse.objects.filter(question=first_nps_q)
        nps_total = nps_responses.count()
        if nps_total > 0:
            total_responses = nps_total
            main_avg_score = round(nps_responses.aggregate(Avg('score_value'))['score_value__avg'] or 0, 1)
            promoters = nps_responses.filter(score_value__gte=9).count()
            passives = nps_responses.filter(score_value__gte=7, score_value__lte=8).count()
            detractors = nps_responses.filter(score_value__lte=6).count()
            main_enps_score = round(((promoters - detractors) / nps_total) * 100, 1)
            enps_score = main_enps_score
            avg_score = main_avg_score
            if nps_total > 0:
                promoters_pct = round((promoters / nps_total) * 100, 1)
                passives_pct = round((passives / nps_total) * 100, 1)
                detractors_pct = round((detractors / nps_total) * 100, 1)
    elif first_rating5_q:
        main_question_type = 'rating_5'
        main_question_text = first_rating5_q.question_text
        rating_responses = ENPSQuestionResponse.objects.filter(question=first_rating5_q)
        rating_total = rating_responses.count()
        if rating_total > 0:
            total_responses = rating_total
            main_avg_score = round(rating_responses.aggregate(Avg('score_value'))['score_value__avg'] or 0, 1)
            avg_score = main_avg_score
            # Rating distribution
            main_rating_dist = []
            for i in range(5, 0, -1):
                count = rating_responses.filter(score_value=i).count()
                pct = round((count / rating_total) * 100, 1) if rating_total > 0 else 0
                main_rating_dist.append({'stars': i, 'count': count, 'pct': pct})
    elif first_rating3_q:
        main_question_type = 'rating_3'
        main_question_text = first_rating3_q.question_text
        rating_responses = ENPSQuestionResponse.objects.filter(question=first_rating3_q)
        rating_total = rating_responses.count()
        if rating_total > 0:
            total_responses = rating_total
            main_avg_score = round(rating_responses.aggregate(Avg('score_value'))['score_value__avg'] or 0, 1)
            avg_score = main_avg_score
            # Rating distribution
            main_rating_dist = []
            for i in range(3, 0, -1):
                count = rating_responses.filter(score_value=i).count()
                pct = round((count / rating_total) * 100, 1) if rating_total > 0 else 0
                main_rating_dist.append({'stars': i, 'count': count, 'pct': pct})
    elif first_yesno_q:
        main_question_type = 'yes_no'
        main_question_text = first_yesno_q.question_text
        yesno_responses = ENPSQuestionResponse.objects.filter(question=first_yesno_q)
        yesno_total = yesno_responses.count()
        if yesno_total > 0:
            total_responses = yesno_total
            main_yes_count = yesno_responses.filter(boolean_value=True).count()
            main_no_count = yesno_responses.filter(boolean_value=False).count()
            main_yes_pct = round((main_yes_count / yesno_total) * 100, 1)
            main_no_pct = round((main_no_count / yesno_total) * 100, 1)
    else:
        # Fallback to old method (based on ENPSResponse model)
        main_question_type = None
        if total_responses > 0:
            promoters = responses.filter(category='promoter').count()
            passives = responses.filter(category='passive').count()
            detractors = responses.filter(category='detractor').count()
            promoters_pct = round((promoters / total_responses) * 100, 1)
            passives_pct = round((passives / total_responses) * 100, 1)
            detractors_pct = round((detractors / total_responses) * 100, 1)
            avg_score = round(responses.aggregate(Avg('score'))['score__avg'] or 0, 1)
            # Calculate eNPS from responses if not already set
            if promoters > 0 or detractors > 0:
                enps_score = round(((promoters - detractors) / total_responses) * 100, 1)
            else:
                enps_score = survey.enps_score if survey.enps_score else 0
    
    # Override promoters/passives/detractors with question-specific data if available
    if main_enps_score is not None:
        if total_responses > 0:
            promoters_pct = round((promoters / total_responses) * 100, 1)
            passives_pct = round((passives / total_responses) * 100, 1)
            detractors_pct = round((detractors / total_responses) * 100, 1)
    
    # Department breakdown - Calculate based on question type dynamically
    # Get departments from both denormalized field and employee records
    department_stats = []
    
    # Get unique departments from multiple sources:
    # 1. Denormalized department field on ENPSResponse
    # 2. Employee's department via ForeignKey (fallback)
    # 3. From question responses
    dept_from_responses = set(responses.exclude(department='').values_list('department', flat=True).distinct())
    
    # Also get departments from employees who have responded (via ForeignKey)
    dept_from_employees = set()
    responses_with_employee = responses.exclude(employee__isnull=True).select_related('employee', 'employee__departmentlink')
    for r in responses_with_employee:
        if r.employee and r.employee.departmentlink:
            dept_from_employees.add(r.employee.departmentlink.department_name)
    
    # Also get departments from question responses
    dept_from_question_responses = set()
    if questions.exists():
        # Get all question responses with their response's employee
        q_responses = ENPSQuestionResponse.objects.filter(
            question__survey=survey
        ).select_related('response', 'response__employee', 'response__employee__departmentlink')
        for qr in q_responses:
            if qr.response:
                # Check response's department field first
                if qr.response.department:
                    dept_from_question_responses.add(qr.response.department)
                # Then check employee's departmentlink (ForeignKey)
                elif qr.response.employee and qr.response.employee.departmentlink:
                    dept_from_question_responses.add(qr.response.employee.departmentlink.department_name)
    
    # Combine all sources
    all_departments = list(dept_from_responses.union(dept_from_employees).union(dept_from_question_responses))
    
    for dept_name in all_departments:
        # Get responses for this department from both sources
        dept_responses = responses.filter(department=dept_name)
        
        # Also check employee departmentlink if no responses from denormalized field
        if dept_responses.count() == 0:
            dept_responses = responses.filter(employee__departmentlink__department_name=dept_name)
        
        dept_total = dept_responses.count()
        
        dept_data = {
            'department': dept_name,
            'count': dept_total,
            'avg_score': 0,
            'enps_score': 0,
        }
        
        if dept_total > 0:
            if main_question_type == 'nps' or main_question_type is None:
                # Calculate eNPS based on question responses
                first_nps_q = questions.filter(question_type='nps').first()
                if first_nps_q:
                    # Try question responses via department field
                    dept_q_responses = ENPSQuestionResponse.objects.filter(
                        question=first_nps_q,
                        response__department=dept_name
                    )
                    # Also try via employee departmentlink (ForeignKey)
                    if dept_q_responses.count() == 0:
                        dept_q_responses = ENPSQuestionResponse.objects.filter(
                            question=first_nps_q,
                            response__employee__departmentlink__department_name=dept_name
                        )
                    
                    dept_q_total = dept_q_responses.count()
                    if dept_q_total > 0:
                        dept_data['count'] = dept_q_total  # Update to question response count
                        dept_data['avg_score'] = round(dept_q_responses.aggregate(Avg('score_value'))['score_value__avg'] or 0, 1)
                        dept_promoters = dept_q_responses.filter(score_value__gte=9).count()
                        dept_detractors = dept_q_responses.filter(score_value__lte=6).count()
                        dept_data['enps_score'] = round(((dept_promoters - dept_detractors) / dept_q_total) * 100, 1)
                else:
                    # Fallback to old method
                    dept_promoters = dept_responses.filter(score__gte=9).count()
                    dept_detractors = dept_responses.filter(score__lte=6).count()
                    dept_data['avg_score'] = round(dept_responses.aggregate(Avg('score'))['score__avg'] or 0, 1)
                    dept_data['enps_score'] = round(((dept_promoters - dept_detractors) / dept_total) * 100, 1) if dept_total > 0 else 0
            elif main_question_type == 'rating_5':
                first_rating5_q = questions.filter(question_type='rating_5').first()
                if first_rating5_q:
                    dept_q_responses = ENPSQuestionResponse.objects.filter(
                        question=first_rating5_q,
                        response__department=dept_name
                    )
                    if dept_q_responses.count() == 0:
                        dept_q_responses = ENPSQuestionResponse.objects.filter(
                            question=first_rating5_q,
                            response__employee__departmentlink__department_name=dept_name
                        )
                    
                    dept_q_total = dept_q_responses.count()
                    if dept_q_total > 0:
                        dept_data['count'] = dept_q_total
                        dept_data['avg_score'] = round(dept_q_responses.aggregate(Avg('score_value'))['score_value__avg'] or 0, 1)
            elif main_question_type == 'rating_3':
                first_rating3_q = questions.filter(question_type='rating_3').first()
                if first_rating3_q:
                    dept_q_responses = ENPSQuestionResponse.objects.filter(
                        question=first_rating3_q,
                        response__department=dept_name
                    )
                    if dept_q_responses.count() == 0:
                        dept_q_responses = ENPSQuestionResponse.objects.filter(
                            question=first_rating3_q,
                            response__employee__departmentlink__department_name=dept_name
                        )
                    
                    dept_q_total = dept_q_responses.count()
                    if dept_q_total > 0:
                        dept_data['count'] = dept_q_total
                        dept_data['avg_score'] = round(dept_q_responses.aggregate(Avg('score_value'))['score_value__avg'] or 0, 1)
            elif main_question_type == 'yes_no':
                first_yesno_q = questions.filter(question_type='yes_no').first()
                if first_yesno_q:
                    dept_q_responses = ENPSQuestionResponse.objects.filter(
                        question=first_yesno_q,
                        response__department=dept_name
                    )
                    if dept_q_responses.count() == 0:
                        dept_q_responses = ENPSQuestionResponse.objects.filter(
                            question=first_yesno_q,
                            response__employee__departmentlink__department_name=dept_name
                        )
                    
                    dept_q_total = dept_q_responses.count()
                    if dept_q_total > 0:
                        dept_data['count'] = dept_q_total
                        yes_count = dept_q_responses.filter(boolean_value=True).count()
                        dept_data['enps_score'] = round((yes_count / dept_q_total) * 100, 1)  # Yes percentage
                        dept_data['yes_pct'] = dept_data['enps_score']
        
        # Only add departments with responses
        if dept_data['count'] > 0:
            department_stats.append(dept_data)
    
    # Sort by count descending
    department_stats.sort(key=lambda x: x['count'], reverse=True)
    
    # Emoji distribution
    emoji_stats = responses.exclude(emoji_feedback='').values('emoji_feedback').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Get all departments - use the already calculated all_departments from department stats section
    
    # Question-level analytics - calculate based on question type
    questions = survey.questions.all().order_by('order')
    question_analytics = []
    
    for question in questions:
        q_data = {
            'id': question.id,
            'question_text': question.question_text,
            'question_type': question.question_type,
            'is_required': question.is_required,
            'total_responses': 0,
            'avg_score': None,
            'distribution': [],
            'distribution_pct': [],
            'yes_pct': None,
            'no_pct': None,
            'text_responses': [],
        }
        
        # Get all responses for this question
        question_responses = ENPSQuestionResponse.objects.filter(question=question)
        total_q_responses = question_responses.count()
        q_data['total_responses'] = total_q_responses
        
        if total_q_responses > 0:
            if question.question_type == 'nps':
                # NPS: Calculate score distribution and eNPS
                score_counts = {i: 0 for i in range(11)}
                for qr in question_responses:
                    if qr.score_value is not None:
                        score_counts[qr.score_value] = score_counts.get(qr.score_value, 0) + 1
                
                q_data['distribution'] = [score_counts[i] for i in range(11)]
                q_data['distribution_pct'] = [round((score_counts[i] / total_q_responses) * 100, 1) for i in range(11)]
                
                # Calculate eNPS for this question
                promoters = question_responses.filter(score_value__gte=9).count()
                detractors = question_responses.filter(score_value__lte=6).count()
                q_data['avg_score'] = round(question_responses.aggregate(Avg('score_value'))['score_value__avg'] or 0, 1)
                if total_q_responses > 0:
                    q_data['enps_score'] = round(((promoters - detractors) / total_q_responses) * 100, 1)
                else:
                    q_data['enps_score'] = 0
                    
            elif question.question_type in ['rating_5', 'rating_3']:
                # Rating: Show star distribution
                max_rating = 5 if question.question_type == 'rating_5' else 3
                rating_counts = {i: 0 for i in range(1, max_rating + 1)}
                for qr in question_responses:
                    if qr.score_value is not None:
                        rating_counts[qr.score_value] = rating_counts.get(qr.score_value, 0) + 1
                
                q_data['distribution'] = [rating_counts.get(i, 0) for i in range(1, max_rating + 1)]
                q_data['distribution_pct'] = [round((rating_counts.get(i, 0) / total_q_responses) * 100, 1) for i in range(1, max_rating + 1)]
                q_data['avg_score'] = round(question_responses.aggregate(Avg('score_value'))['score_value__avg'] or 0, 1)
                
            elif question.question_type == 'yes_no':
                # Yes/No: Calculate percentages
                yes_count = question_responses.filter(boolean_value=True).count()
                no_count = question_responses.filter(boolean_value=False).count()
                q_data['yes_count'] = yes_count
                q_data['no_count'] = no_count
                q_data['yes_pct'] = round((yes_count / total_q_responses) * 100, 1) if total_q_responses > 0 else 0
                q_data['no_pct'] = round((no_count / total_q_responses) * 100, 1) if total_q_responses > 0 else 0
                
            elif question.question_type == 'text':
                # Text: Get sample responses
                text_responses = list(question_responses.exclude(text_value='').values_list('text_value', flat=True)[:10])
                q_data['text_responses'] = text_responses
        
        question_analytics.append(q_data)
    
    # Score distribution - use question responses if available, otherwise fallback to base responses
    score_distribution = [0] * 11
    
    # If we have NPS question responses, use them for the distribution
    if first_nps_q:
        nps_responses = ENPSQuestionResponse.objects.filter(question=first_nps_q)
        for qr in nps_responses:
            if qr.score_value is not None and 0 <= qr.score_value <= 10:
                score_distribution[qr.score_value] += 1
    else:
        # Fallback to old method using base responses
        for r in responses:
            if 0 <= r.score <= 10:
                score_distribution[r.score] += 1
    
    # Use dynamic stats if available, otherwise fallback to main response stats
    # For non-NPS question types, show the avg_score instead of enps_score
    final_enps_score = main_enps_score if main_enps_score is not None else enps_score
    final_avg_score = main_avg_score if main_avg_score is not None else avg_score
    
    # For display: if question type is rating or yes_no, use avg_score for enps_score display
    # For NPS, show avg_score when eNPS is 0 (more informative)
    if main_question_type in ['rating_5', 'rating_3'] and final_avg_score is not None:
        display_score = final_avg_score
    elif main_question_type == 'yes_no' and main_yes_pct is not None:
        display_score = main_yes_pct
    elif main_question_type == 'nps' and final_enps_score == 0 and final_avg_score is not None and final_avg_score > 0:
        # When eNPS is 0, show average score instead (more meaningful)
        display_score = final_avg_score
    else:
        display_score = final_enps_score
    
    # Calculate combined average for the gauge chart (similar to survey_detail)
    combined_avg = final_avg_score if final_avg_score is not None else 0
    
    # Enhance department_stats with additional fields for the charts
    # Get active employees by department for expected counts
    active_employees_by_dept = {}
    for staff in Staff.objects.filter(status='active'):
        if staff.departmentlink:
            dept_name = staff.departmentlink.department_name
            active_employees_by_dept[dept_name] = active_employees_by_dept.get(dept_name, 0) + 1
    
    # Add respondents, expected, response_rate, satisfaction to each dept
    enhanced_dept_stats = []
    for dept in department_stats:
        dept_name = dept.get('department', '')
        expected_count = active_employees_by_dept.get(dept_name, 0)
        respondent_count = dept.get('count', 0)
        response_rate = round((respondent_count / expected_count * 100), 1) if expected_count > 0 else 0
        satisfaction = dept.get('avg_score', 0)
        
        enhanced_dept_stats.append({
            'department': dept_name,
            'respondents': respondent_count,
            'expected': expected_count,
            'response_rate': response_rate,
            'satisfaction': satisfaction,
            'enps': dept.get('enps_score', 0),
            'count': respondent_count,
            'avg_score': satisfaction,
            'enps_score': dept.get('enps_score', 0),
        })
    
    context = {
        'survey': survey,
        'questions': questions,
        'question_analytics': question_analytics,
        'total_responses': total_responses,
        'enps_score': display_score,
        'raw_enps_score': final_enps_score,  # Original eNPS score before fallback to avg
        'display_score': display_score,  # What actually shows on the card
        'promoters': promoters,
        'promoters_pct': promoters_pct,
        'passives': passives,
        'passives_pct': passives_pct,
        'detractors': detractors,
        'detractors_pct': detractors_pct,
        'avg_score': final_avg_score,
        'combined_avg': combined_avg,
        'department_stats': enhanced_dept_stats,
        'score_distribution': score_distribution,
        'emoji_stats': list(emoji_stats),
        'all_departments': all_departments,
        'page_title': f'Analytics: {survey.name}',
        # Dynamic main stats based on question type
        'main_question_type': main_question_type,
        'main_question_text': main_question_text,
        'main_rating_dist': main_rating_dist,
        'main_yes_count': main_yes_count,
        'main_no_count': main_no_count,
        'main_yes_pct': main_yes_pct,
        'main_no_pct': main_no_pct,
    }
    return render(request, 'hr/default/survey/enps/analytics.html', context)


# ═══════════════════════════════════════════════════════════════════════════════
# Employee-Facing Survey Form
# ═══════════════════════════════════════════════════════════════════════════════

def enps_take_survey(request, survey_id):
    """Employee-facing survey form"""
    from django.utils import timezone
    from datetime import timedelta
    
    survey = get_object_or_404(ENPSSurvey, id=survey_id)
    
    # Check if survey is open (use is_active field)
    if not survey.is_active:
        return render(request, 'hr/default/survey/enps/survey_closed.html', {
            'survey': survey,
            'page_title': 'Survey Closed'
        })
    
    # Get current period (month-year)
    now = timezone.now()
    current_period = now.strftime('%B %Y')  # e.g., "March 2026"
    current_month = now.month
    current_year = now.year
    
    # Get start and end of current month for filtering
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if current_month == 12:
        month_end = now.replace(year=current_year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0) - timedelta(seconds=1)
    else:
        month_end = now.replace(month=current_month + 1, day=1, hour=0, minute=0, second=0, microsecond=0) - timedelta(seconds=1)
    
    # Check if user already responded this month (via hash)
    already_responded = False
    responded_period = None
    
    # Check authentication via session (custom auth system)
    is_authenticated = request.session.get('employee_number') is not None
    if is_authenticated:
        try:
            employee_id = request.session.get('employee_id')
            if employee_id:
                staff = Staff.objects.get(id=employee_id)
            else:
                emp_num = request.session.get('employee_number')
                staff = Staff.objects.get(employee_number=emp_num)
            emp_hash = ENPSResponse.hash_value(staff.employee_number)
            email_hash = ENPSResponse.hash_value(staff.email_address)
            
            # Check if user responded this month
            responses_this_month = survey.responses.filter(
                employee_number_hash=emp_hash,
                created_at__gte=month_start,
                created_at__lte=month_end
            ) | survey.responses.filter(
                email_hash=email_hash,
                created_at__gte=month_start,
                created_at__lte=month_end
            )
            
            already_responded = responses_this_month.exists()
            
            # If responded before, get the period
            if not already_responded:
                past_response = survey.responses.filter(
                    employee_number_hash=emp_hash
                ).first() or survey.responses.filter(
                    email_hash=email_hash
                ).first()
                if past_response:
                    responded_period = past_response.created_at.strftime('%B %Y')
        except (Staff.DoesNotExist, AttributeError, TypeError):
            pass
    
    context = {
        'survey': survey,
        'already_responded': already_responded,
        'current_period': current_period,
        'responded_period': responded_period,
        'page_title': f'{survey.name}',
    }
    return render(request, 'hr/default/survey/enps/survey_take.html', context)


@require_http_methods(["POST"])
def enps_submit_response(request, survey_id):
    """Handle survey submission"""
    from django.utils import timezone
    from datetime import timedelta
    
    survey = get_object_or_404(ENPSSurvey, id=survey_id)
    
    if not survey.is_active:
        return JsonResponse({'success': False, 'error': 'Survey is closed'}, status=400)
    
    # Get current month range for duplicate check
    now = timezone.now()
    current_month = now.month
    current_year = now.year
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if current_month == 12:
        month_end = now.replace(year=current_year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0) - timedelta(seconds=1)
    else:
        month_end = now.replace(month=current_month + 1, day=1, hour=0, minute=0, second=0, microsecond=0) - timedelta(seconds=1)
    
    is_anonymous = request.POST.get('is_anonymous') == '1' or request.POST.get('is_anonymous') == 'true'
    
    # Get employee info if authenticated and not anonymous
    employee = None
    department = ''
    emp_hash = None
    email_hash = None
    
    # Check authentication via session (custom auth system)
    is_authenticated = request.session.get('employee_number') is not None
    
    if not is_anonymous and is_authenticated:
        try:
            employee_id = request.session.get('employee_id')
            if employee_id:
                employee = Staff.objects.get(id=employee_id)
                # Use departmentlink (ForeignKey) for department info
                department = employee.departmentlink.department_name if employee.departmentlink else ''
                emp_hash = ENPSResponse.hash_value(employee.employee_number)
                email_hash = ENPSResponse.hash_value(employee.email_address)
            else:
                # Fallback: try to get by employee_number
                emp_num = request.session.get('employee_number')
                if emp_num:
                    employee = Staff.objects.get(employee_number=emp_num)
                    department = employee.departmentlink.department_name if employee.departmentlink else ''
                    emp_hash = ENPSResponse.hash_value(employee.employee_number)
                    email_hash = ENPSResponse.hash_value(employee.email_address)
        except (Staff.DoesNotExist, AttributeError, TypeError):
            is_anonymous = True
    
    # Check if user already responded this month (prevent duplicate submissions)
    if emp_hash or email_hash:
        duplicate_check = survey.responses.filter(
            created_at__gte=month_start,
            created_at__lte=month_end
        )
        if emp_hash:
            duplicate_check = duplicate_check.filter(employee_number_hash=emp_hash)
        if email_hash:
            duplicate_check = duplicate_check.filter(email_hash=email_hash)
        
        if duplicate_check.exists():
            return JsonResponse({
                'success': False, 
                'error': 'You have already submitted feedback for this month. You can submit again next month!'
            }, status=400)
    
    # Get all questions for this survey
    questions = survey.questions.all()
    
    # Validate required questions
    errors = []
    for question in questions:
        if question.is_required:
            answer_found = False
            
            if question.question_type == 'nps':
                score = request.POST.get(f'score_{question.id}')
                if score:
                    answer_found = True
            elif question.question_type == 'rating_5':
                rating = request.POST.get(f'rating_{question.id}')
                if rating:
                    answer_found = True
            elif question.question_type == 'rating_3':
                rating = request.POST.get(f'rating_{question.id}')
                if rating:
                    answer_found = True
            elif question.question_type == 'text':
                text = request.POST.get(f'text_{question.id}', '').strip()
                if text:
                    answer_found = True
            elif question.question_type == 'yes_no':
                boolean = request.POST.get(f'boolean_{question.id}')
                if boolean:
                    answer_found = True
            
            if not answer_found:
                errors.append(f'Question "{question.question_text[:30]}..." is required')
    
    if errors:
        return JsonResponse({'success': False, 'error': '; '.join(errors)}, status=400)
    
    # Calculate main score (for ENPS category) - use first NPS question or first rating question
    main_score = None
    main_emoji = '😐'
    
    # Find first NPS or rating question to determine main score
    for question in questions.order_by('order'):
        if question.question_type == 'nps':
            score_str = request.POST.get(f'score_{question.id}')
            if score_str:
                main_score = int(score_str)
                # Determine emoji based on score
                if main_score >= 9:
                    main_emoji = '😄'
                elif main_score >= 7:
                    main_emoji = '🙂'
                elif main_score >= 5:
                    main_emoji = '😐'
                elif main_score >= 3:
                    main_emoji = '😕'
                else:
                    main_emoji = '😞'
                break
        elif question.question_type in ['rating_5', 'rating_3']:
            rating_str = request.POST.get(f'rating_{question.id}')
            if rating_str:
                main_score = int(rating_str)
                # Map rating to NPS-like emoji
                if question.question_type == 'rating_5':
                    if main_score >= 4:
                        main_emoji = '😄'
                    elif main_score >= 3:
                        main_emoji = '🙂'
                    else:
                        main_emoji = '😕'
                else:  # rating_3
                    if main_score >= 2:
                        main_emoji = '🙂'
                    else:
                        main_emoji = '😕'
                break
    
    # If no score from questions, use default
    if main_score is None:
        main_score = 5  # Default neutral score
    
    # Determine category based on main score
    if main_score >= 9:
        category = 'promoter'
    elif main_score >= 7:
        category = 'passive'
    else:
        category = 'detractor'
    
    # Create main ENPSResponse
    response = ENPSResponse.objects.create(
        survey=survey,
        score=main_score,
        emoji_feedback=main_emoji,
        feedback_comment='',  # Could collect from a comment field if needed
        is_anonymous=is_anonymous,
        employee=employee,
        department=department,
        employee_number_hash=emp_hash,
        email_hash=email_hash,
        ip_address=get_client_ip(request) if not is_anonymous else None
    )
    
    # Create ENPSQuestionResponse for each question
    for question in questions:
        question_type = question.question_type
        score_value = None
        text_value = None
        boolean_value = None
        
        if question_type == 'nps':
            score_str = request.POST.get(f'score_{question.id}')
            if score_str:
                score_value = int(score_str)
        elif question_type == 'rating_5':
            rating_str = request.POST.get(f'rating_{question.id}')
            if rating_str:
                score_value = int(rating_str)
        elif question_type == 'rating_3':
            rating_str = request.POST.get(f'rating_{question.id}')
            if rating_str:
                score_value = int(rating_str)
        elif question_type == 'text':
            text_value = request.POST.get(f'text_{question.id}', '').strip()
        elif question_type == 'yes_no':
            boolean_str = request.POST.get(f'boolean_{question.id}')
            if boolean_str:
                boolean_value = boolean_str == '1' or boolean_str == 'true'
        
        # Only create response if there's an answer
        if score_value is not None or text_value or boolean_value is not None:
            ENPSQuestionResponse.objects.create(
                response=response,
                question=question,
                score_value=score_value,
                text_value=text_value or '',
                boolean_value=boolean_value
            )
    
    # Update department analytics cache
    update_department_analytics(survey, department)
    
    return JsonResponse({
        'success': True, 
        'message': 'Thank you for your feedback!',
        'category': category
    })


def update_department_analytics(survey, department_name):
    """
    Update cached department analytics for a survey.
    This function recalculates and stores department-level metrics.
    """
    if not department_name:
        return
    
    responses = survey.responses.filter(department=department_name)
    total = responses.count()
    
    if total == 0:
        return
    
    # Calculate metrics
    promoters = responses.filter(category='promoter').count()
    passives = responses.filter(category='passive').count()
    detractors = responses.filter(category='detractor').count()
    avg_score = responses.aggregate(Avg('score'))['score__avg'] or 0
    
    # Calculate eNPS
    enps = round(((promoters - detractors) / total) * 100, 1) if total > 0 else 0
    
    # Get emoji distribution
    emoji_dist = {}
    for emoji_choice in ENPSResponse.EMOJI_CHOICES:
        emoji = emoji_choice[0]
        count = responses.filter(emoji_feedback=emoji).count()
        if count > 0:
            emoji_dist[emoji] = count
    
    # Get Staff info for this department
    try:
        from App.users.models import Staff
        staff_in_dept = Staff.objects.filter(department=department_name, status='active').count()
    except:
        staff_in_dept = 0
    
    # Update or create the analytics record
    ENPSDepartmentAnalytics.objects.update_or_create(
        survey=survey,
        department=department_name,
        defaults={
            'total_responses': total,
            'enps_score': enps,
            'promoters_count': promoters,
            'passives_count': passives,
            'detractors_count': detractors,
            'average_score': round(avg_score, 1),
            'emoji_distribution': emoji_dist,
        }
    )


def refresh_all_department_analytics(request, survey_id):
    """
    Management endpoint to refresh all department analytics for a survey.
    Call this after bulk imports or data corrections.
    """
    survey = get_object_or_404(ENPSSurvey, id=survey_id)
    
    # Get all departments with responses
    departments = survey.responses.exclude(department='').values_list('department', flat=True).distinct()
    
    updated_count = 0
    for dept in departments:
        update_department_analytics(survey, dept)
        updated_count += 1
    
    return JsonResponse({
        'success': True,
        'message': f'Updated analytics for {updated_count} departments'
    })


def get_client_ip(request):
    """Get client IP address"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


# ═══════════════════════════════════════════════════════════════════════════════
# HTMX AJAX Endpoints
# ═══════════════════════════════════════════════════════════════════════════════

def enps_responses_ajax(request, survey_id):
    """HTMX endpoint for responses table"""
    survey = get_object_or_404(ENPSSurvey, id=survey_id)
    responses = survey.responses.all().order_by('-created_at')
    
    # Simple search
    search = request.GET.get('search')
    if search:
        responses = responses.filter(
            Q(feedback_comment__icontains=search) |
            Q(department__icontains=search)
        )
    
    # Filter by category
    category = request.GET.get('category')
    if category:
        responses = responses.filter(category=category)
    
    # Pagination
    paginator = Paginator(responses, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    html = render_to_string('hr/default/survey/enps/partials/responses_table.html', {
        'page_obj': page_obj,
    })
    
    return HttpResponse(html)


def enps_department_data_ajax(request, survey_id):
    """AJAX endpoint for department chart data"""
    survey = get_object_or_404(ENPSSurvey, id=survey_id)
    responses = survey.responses.all()
    
    department_stats = responses.exclude(department='').values('department').annotate(
        count=Count('id'),
        avg_score=Avg('score')
    ).order_by('-count')[:10]
    
    # Calculate eNPS for each department
    data = []
    for dept in department_stats:
        dept_responses = responses.filter(department=dept['department'])
        dept_total = dept_responses.count()
        if dept_total > 0:
            dept_promoters = dept_responses.filter(score__gte=9).count()
            dept_detractors = dept_responses.filter(score__lte=6).count()
            dept_enps = round(((dept_promoters - dept_detractors) / dept_total) * 100, 1)
        else:
            dept_enps = 0
        
        data.append({
            'department': dept['department'],
            'count': dept_total,
            'avg_score': round(dept['avg_score'] or 0, 1),
            'enps': dept_enps
        })
    
    return JsonResponse({'data': data})


def enps_trend_data_ajax(request, survey_id):
    """AJAX endpoint for trend chart data"""
    survey = get_object_or_404(ENPSSurvey, id=survey_id)
    responses = survey.responses.all()
    
    # Get monthly trends
    from django.db.models.functions import TruncMonth
    monthly_data = responses.annotate(
        month=TruncMonth('created_at')
    ).values('month').annotate(
        count=Count('id'),
        avg_score=Avg('score'),
        promoters=Count('id', filter=Q(score__gte=9)),
        detractors=Count('id', filter=Q(score__lte=6))
    ).order_by('month')
    
    data = []
    for item in monthly_data:
        total = item['count']
        if total > 0:
            enps = round(((item['promoters'] - item['detractors']) / total) * 100, 1)
        else:
            enps = 0
        
        data.append({
            'month': item['month'].strftime('%Y-%m') if item['month'] else '',
            'count': total,
            'avg_score': round(item['avg_score'] or 0, 1),
            'enps': enps
        })
    
    return JsonResponse({'data': data})


def enps_heatmap_data_ajax(request, survey_id):
    """AJAX endpoint for heatmap data (department x month)"""
    survey = get_object_or_404(ENPSSurvey, id=survey_id)
    responses = survey.responses.all()
    
    from django.db.models.functions import TruncMonth
    
    # Get data grouped by department and month
    heatmap_data = responses.exclude(department='').annotate(
        month=TruncMonth('created_at')
    ).values('department', 'month').annotate(
        count=Count('id'),
        avg_score=Avg('score'),
        promoters=Count('id', filter=Q(score__gte=9)),
        detractors=Count('id', filter=Q(score__lte=6))
    ).order_by('month', 'department')
    
    # Organize data for heatmap
    departments = set()
    months = set()
    matrix = {}
    
    for item in heatmap_data:
        dept = item['department']
        month_key = item['month'].strftime('%Y-%m') if item['month'] else ''
        
        departments.add(dept)
        months.add(month_key)
        
        total = item['count']
        if total > 0:
            enps = round(((item['promoters'] - item['detractors']) / total) * 100, 1)
        else:
            enps = None
        
        matrix[f"{dept}|{month_key}"] = {
            'count': total,
            'avg_score': round(item['avg_score'] or 0, 1),
            'enps': enps
        }
    
    return JsonResponse({
        'departments': sorted(list(departments)),
        'months': sorted(list(months)),
        'matrix': matrix
    })


# ═══════════════════════════════════════════════════════════════════════════════
# Utility Views
# ═══════════════════════════════════════════════════════════════════════════════

def enps_response_detail(request, response_id):
    """View individual response details (HR only)"""
    response = get_object_or_404(ENPSResponse, id=response_id)
    
    # If anonymous, hide employee info
    if response.is_anonymous:
        employee_info = None
    else:
        employee_info = {
            'employee': response.employee,
            'department': response.department,
            'submitted_at': response.created_at,
        }
    
    context = {
        'response': response,
        'employee_info': employee_info,
        'page_title': 'Response Details',
    }
    return render(request, 'hr/default/survey/enps/response_detail.html', context)


@require_http_methods(["GET"])
def lookup_employee(request):
    """
    API endpoint to lookup employee by employee number.
    Returns employee name without revealing full identity publicly.
    Used in survey detail page for HR to identify respondents.
    """
    employee_id = request.GET.get('employee_id', '').strip()
    
    if not employee_id:
        return JsonResponse({'error': 'Employee ID is required'}, status=400)
    
    try:
        from App.users.models import Staff
        
        # Try to find employee by employee_number
        employee = Staff.objects.filter(employee_number__iexact=employee_id).first()
        
        if employee:
            department_name = None
            if employee.departmentlink:
                department_name = employee.departmentlink.department_name
            elif employee.department:
                department_name = employee.department
            
            return JsonResponse({
                'found': True,
                'employee_name': f"{employee.first_name} {employee.last_name}",
                'employee_number': employee.employee_number,
                'department': department_name,
            })
        else:
            return JsonResponse({'found': False, 'error': 'Employee not found'})
            
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
