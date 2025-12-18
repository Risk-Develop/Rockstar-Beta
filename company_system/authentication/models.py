from django.db import models
from django.contrib.auth.hashers import make_password, check_password
from users.models import Staff


# ------------------------
# User Account Table
# ------------------------
class UserAccount(models.Model):
    employee = models.OneToOneField(Staff, on_delete=models.CASCADE, verbose_name="Employee")
    password = models.CharField("Password", max_length=255)  # store hashed password
    created_at = models.DateTimeField("Created At", auto_now_add=True)
    last_login = models.DateTimeField("Last Login", null=True, blank=True)

    def __str__(self):
        return f"Account for {self.employee.employee_number}"

    # ------------------------
    # Set and Check Password
    # ------------------------
    def set_password(self, raw_password):
        self.password = make_password(raw_password)
        self.save(update_fields=["password"])

    def check_password(self, raw_password):
        return check_password(raw_password, self.password)