from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0003_add_ev_fields'),
    ]

    operations = [
        # Add notification preferences field
        migrations.AddField(
            model_name='customuser',
            name='notification_preferences',
            field=models.TextField(blank=True, null=True),
        ),
        # Add unread notifications count
        migrations.AddField(
            model_name='customuser',
            name='unread_notifications',
            field=models.PositiveIntegerField(default=0),
        ),
        # Create Notification model
        migrations.CreateModel(
            name='Notification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('notification_type', models.CharField(choices=[('system', 'System'), ('station_update', 'Station Update'), ('booking', 'Booking'), ('payment', 'Payment'), ('maintenance', 'Maintenance'), ('marketing', 'Marketing')], default='system', max_length=20)),
                ('title', models.CharField(max_length=255)),
                ('message', models.TextField()),
                ('link', models.CharField(blank=True, max_length=255, null=True)),
                ('is_read', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='notifications', to='authentication.customuser')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]
