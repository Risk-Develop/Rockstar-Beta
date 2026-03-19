# Generated migration for PayoutDetail model changes
# Adds leave_days_paid and leave_days_unpaid fields

from django.db import migrations, models
from decimal import Decimal


class Migration(migrations.Migration):

    dependencies = [
        ('human_resource', '0022_payroll_enhancement'),
    ]

    operations = [
        migrations.AddField(
            model_name='payoutdetail',
            name='leave_days_paid',
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal('0.00'),
                help_text='Paid leave days (adds to earnings)',
                max_digits=6
            ),
        ),
        migrations.AddField(
            model_name='payoutdetail',
            name='leave_days_unpaid',
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal('0.00'),
                help_text='Unpaid leave days (deducts from earnings)',
                max_digits=6
            ),
        ),
    ]

