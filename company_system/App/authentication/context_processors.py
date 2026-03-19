"""
Context processor to add session info to all templates
"""
from App.authentication.views import get_current_employee


def session_context(request):
    """Add session timeout info and current employee to template context"""
    # Get the current employee for the sidebar profile card
    employee = get_current_employee(request)
    is_owner = request.session.get('is_owner', False)
    
    if request.session.get('employee_number'):
        from django.conf import settings
        idle_timeout = getattr(settings, 'IDLE_SESSION_TIMEOUT', 1800)
        
        # Get last activity
        last_activity = request.session.get('last_activity')
        if last_activity:
            from django.utils import timezone
            from datetime import datetime
            
            last_time = None
            try:
                # Parse ISO format - timezone.now().isoformat() produces timezone-aware string
                # But datetime.fromisoformat() in Python returns naive datetime
                # So we need to make it timezone-aware
                parsed = datetime.fromisoformat(last_activity)
                # Handle both naive and timezone-aware strings
                if parsed.tzinfo is None:
                    # It's naive, make it timezone-aware using Django's timezone
                    last_time = timezone.make_aware(parsed, timezone.get_current_timezone())
                else:
                    last_time = parsed
            except (ValueError, TypeError):
                last_time = None
            
            if last_time:
                current_time = timezone.now()
                idle_seconds = (current_time - last_time).total_seconds()
                remaining = int(idle_timeout - idle_seconds)
                
                return {
                    'employee': employee,
                    'is_owner': is_owner,
                    'session_remaining_seconds': remaining,
                    'session_warning_seconds': 300,
                }
    
    return {
        'employee': employee,
        'is_owner': is_owner,
        'session_remaining_seconds': 0,
        'session_warning_seconds': 300,
    }

