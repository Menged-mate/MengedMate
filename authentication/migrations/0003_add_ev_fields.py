from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0002_add_profile_and_reset_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='ev_battery_capacity_kwh',
            field=models.DecimalField(blank=True, decimal_places=2, help_text='Battery capacity in kWh', max_digits=6, null=True),
        ),
        migrations.AddField(
            model_name='customuser',
            name='ev_connector_type',
            field=models.CharField(blank=True, choices=[('type1', 'Type 1 (J1772)'), ('type2', 'Type 2 (Mennekes)'), ('ccs1', 'CCS Combo 1'), ('ccs2', 'CCS Combo 2'), ('chademo', 'CHAdeMO'), ('tesla', 'Tesla'), ('other', 'Other'), ('none', 'None')], default='none', max_length=20),
        ),
    ]
