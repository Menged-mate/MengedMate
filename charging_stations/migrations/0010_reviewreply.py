# Generated migration for ReviewReply model

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('charging_stations', '0009_stationreview'),
    ]

    operations = [
        migrations.CreateModel(
            name='ReviewReply',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('reply_text', models.TextField(help_text='Reply text from station owner')),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('review', models.OneToOneField(help_text='The review this reply is responding to', on_delete=django.db.models.deletion.CASCADE, related_name='reply', to='charging_stations.stationreview')),
                ('station_owner', models.ForeignKey(help_text='Station owner who wrote the reply', on_delete=django.db.models.deletion.CASCADE, related_name='review_replies', to='charging_stations.stationowner')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='reviewreply',
            index=models.Index(fields=['review', '-created_at'], name='charging_st_review__b8e8a5_idx'),
        ),
        migrations.AddIndex(
            model_name='reviewreply',
            index=models.Index(fields=['station_owner', '-created_at'], name='charging_st_station_8b4e8a_idx'),
        ),
    ]
