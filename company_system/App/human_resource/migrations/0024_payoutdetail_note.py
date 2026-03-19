# Generated migration for PayoutDetail.note field
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('human_resource', '0023_payoutdetail_leave_days'),
    ]

    operations = [
        migrations.AddField(
            model_name='payoutdetail',
            name='note',
            field=models.TextField(blank=True, default='', help_text='Additional notes or remarks for this payroll'),
        ),
    ]

