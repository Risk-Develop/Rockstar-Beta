from django.db import models
from django.contrib.auth.hashers import make_password, check_password
from App.users.models import Staff


# ------------------------
# User Account Table
# ------------------------
class UserAccount(models.Model):
    employee = models.OneToOneField(Staff, on_delete=models.CASCADE, verbose_name="Employee")
    password = models.CharField("Password", max_length=255)  # store hashed password
    is_active = models.BooleanField("Active", default=True)  # Can be deactivated by admin
    created_at = models.DateTimeField("Created At", auto_now_add=True)
    last_login = models.DateTimeField("Last Login", null=True, blank=True)

    def __str__(self):
        status = "Active" if self.is_active else "Inactive"
        return f"Account for {self.employee.employee_number} ({status})"

    # ------------------------
    # Set and Check Password
    # ------------------------
    def set_password(self, raw_password):
        self.password = make_password(raw_password)
        self.save(update_fields=["password"])

    def check_password(self, raw_password):
        return check_password(raw_password, self.password)


# ------------------------
# Login History / Audit Trail
# ------------------------
class LoginHistory(models.Model):
    """Track all login attempts for security audit"""
    employee = models.ForeignKey(Staff, on_delete=models.CASCADE, null=True, blank=True)
    employee_number = models.CharField(max_length=50, blank=True)  # Store even if not found
    login_time = models.DateTimeField("Login Time", auto_now_add=True)
    ip_address = models.GenericIPAddressField("IP Address", null=True, blank=True)
    user_agent = models.CharField("Browser", max_length=255, blank=True)
    status = models.CharField("Status", max_length=20)  # 'success' or 'failed'
    failure_reason = models.CharField("Failure Reason", max_length=100, blank=True)

    class Meta:
        ordering = ['-login_time']  # Most recent first
        verbose_name_plural = "Login Histories"

    def __str__(self):
        return f"{self.employee_number} - {self.login_time} - {self.status}"

    def get_browser_name(self):
        """Parse and return the browser name from user agent string"""
        if not self.user_agent:
            return '-'
        
        user_agent = self.user_agent.lower()
        
        # Check for Chrome first (before Safari since Chrome contains Safari)
        if 'chrome' in user_agent and 'edg' not in user_agent:
            return 'Chrome'
        elif 'edg' in user_agent:  # Edge
            return 'Edge'
        elif 'firefox' in user_agent:
            return 'Firefox'
        elif 'safari' in user_agent and 'chrome' not in user_agent:
            return 'Safari'
        elif 'opera' in user_agent or 'opr' in user_agent:
            return 'Opera'
        elif 'msie' in user_agent or 'trident' in user_agent:
            return 'Internet Explorer'
        else:
            return 'Unknown'

    def get_os_name(self):
        """Parse and return the OS name from user agent string"""
        if not self.user_agent:
            return '-'
        
        user_agent = self.user_agent.lower()
        
        # Windows versions
        if 'windows nt 10.0' in user_agent:
            return 'Windows 11/10'
        elif 'windows nt 6.3' in user_agent:
            return 'Windows 8.1'
        elif 'windows nt 6.2' in user_agent:
            return 'Windows 8'
        elif 'windows nt 6.1' in user_agent:
            return 'Windows 7'
        elif 'windows nt 6.0' in user_agent:
            return 'Windows Vista'
        elif 'windows' in user_agent:
            return 'Windows'
        # macOS
        elif 'mac os x' in user_agent:
            # Try to get version
            import re
            match = re.search(r'mac os x ([\d_]+)', user_agent)
            if match:
                version = match.group(1).replace('_', '.')
                return f'macOS {version}'
            return 'macOS'
        # Linux
        elif 'linux' in user_agent:
            if 'ubuntu' in user_agent:
                return 'Ubuntu (Linux)'
            elif 'fedora' in user_agent:
                return 'Fedora (Linux)'
            elif 'debian' in user_agent:
                return 'Debian (Linux)'
            return 'Linux'
        # Mobile
        elif 'android' in user_agent:
            return 'Android'
        elif 'iphone' in user_agent:
            return 'iOS (iPhone)'
        elif 'ipad' in user_agent:
            return 'iPadOS (iPad)'
        else:
            return 'Unknown'

    def get_device_type(self):
        """Parse and return device type from user agent string"""
        if not self.user_agent:
            return '-'
        
        user_agent = self.user_agent.lower()
        
        # Mobile devices
        if 'mobile' in user_agent or 'android' in user_agent:
            if 'tablet' in user_agent or 'ipad' in user_agent:
                return 'Tablet'
            return 'Mobile'
        # Check for common mobile patterns
        elif 'iphone' in user_agent or 'ipod' in user_agent:
            return 'Mobile'
        elif 'ipad' in user_agent:
            return 'Tablet'
        # Check for desktop
        elif 'windows' in user_agent or 'macintosh' in user_agent or 'linux' in user_agent:
            return 'Desktop'
        else:
            return 'Desktop'

    def get_location(self):
        """Get location from IP address using ipapi.co (free tier)"""
        if not self.ip_address or self.ip_address in ['127.0.0.1', 'localhost', '::1']:
            return 'Local'
        
        # Check if it's a private IP
        try:
            parts = self.ip_address.split('.')
            if len(parts) == 4:
                first = int(parts[0])
                second = int(parts[1])
                # Private IP ranges: 10.x.x.x, 172.16-31.x.x, 192.168.x.x
                if first == 10 or (first == 172 and 16 <= second <= 31) or (first == 192 and second == 168):
                    return 'Local Network'
        except:
            pass
        
        # Return IP for now - geolocation requires external API
        # Can integrate with ipapi.co, ipstack, or similar services
        return self.ip_address
