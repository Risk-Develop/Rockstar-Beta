"""
Idle Session Timeout Middleware
Automatically logs out users after a period of inactivity
"""
from django.conf import settings
from django.contrib import messages
from django.shortcuts import redirect
from django.utils import timezone
import datetime


class IdleSessionTimeoutMiddleware:
    """
    Middleware to expire sessions after period of inactivity
    """
    def __init__(self, get_response):
        self.get_response = get_response
        self.idle_timeout = getattr(settings, 'IDLE_SESSION_TIMEOUT', 1800)  # Default 30 min
        self.warning_time = getattr(settings, 'IDLE_SESSION_TIMEOUT_WARNING', 300)  # 5 min warning

    def __call__(self, request):
        # Only check for authenticated users
        if request.session.get('employee_number'):
            # Get last activity time from session
            last_activity = request.session.get('last_activity')
            
            if last_activity:
                # Convert to datetime using Django's timezone
                # Note: timezone.now().isoformat() produces timezone-aware string
                # but fromisoformat returns naive datetime, so we need to make it aware
                try:
                    parsed = timezone.datetime.fromisoformat(last_activity)
                    if parsed.tzinfo is None:
                        last_activity_time = timezone.make_aware(parsed, timezone.get_current_timezone())
                    else:
                        last_activity_time = parsed
                except (ValueError, TypeError):
                    last_activity_time = None
                
                if last_activity_time:
                    current_time = timezone.now()
                    
                    # Calculate idle time in seconds
                    idle_seconds = (current_time - last_activity_time).total_seconds()
                    
                    # Check if session has expired
                    if idle_seconds > self.idle_timeout:
                        # Session expired due to inactivity - log to LoginHistory
                        employee_number = request.session.get('employee_number')
                        self._create_login_history(
                            request=request,
                            employee_number=employee_number,
                            status='failed',
                            failure_reason=f'Session expired due to inactivity ({int(idle_seconds)}s idle)'
                        )
                        
                        # Flush session and redirect
                        request.session.flush()
                        messages.warning(request, "Your session has expired due to inactivity. Please login again.")
                        return redirect('login')
                    
                    # Pass remaining time to template for countdown
                    remaining_time = self.idle_timeout - idle_seconds
                    request.session['session_remaining_seconds'] = int(remaining_time)
                    request.session['session_warning_seconds'] = self.warning_time
        
        # Update last activity time for every request
        if request.session.get('employee_number'):
            request.session['last_activity'] = timezone.now().isoformat()

        response = self.get_response(request)
        return response
    
    def _create_login_history(self, request, employee_number, status, failure_reason):
        """Helper method to create login history entry"""
        try:
            from App.authentication.models import LoginHistory
            from App.users.models import Staff
            
            # Try to get the Staff object
            employee = None
            try:
                employee = Staff.objects.get(employee_number=employee_number)
            except Staff.DoesNotExist:
                employee = None
            
            # Get IP address
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                ip_address = x_forwarded_for.split(',')[0].strip()
            else:
                ip_address = request.META.get('REMOTE_ADDR', '')
            
            # Get user agent
            user_agent = request.META.get('HTTP_USER_AGENT', '')[:255]
            
            # Create the login history entry
            LoginHistory.objects.create(
                employee=employee,
                employee_number=employee_number,
                ip_address=ip_address,
                user_agent=user_agent,
                status=status,
                failure_reason=failure_reason
            )
        except Exception:
            # Don't break the app if logging fails
            pass

