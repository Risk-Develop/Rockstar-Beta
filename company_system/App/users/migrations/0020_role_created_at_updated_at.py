# Generated migration to add created_at and updated_at to Role model

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0019_add_hr_role'),
    ]

    operations = [
        migrations.AddField(
            model_name='role',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
        migrations.AddField(
            model_name='role',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, null=True),
        ),
    ]

