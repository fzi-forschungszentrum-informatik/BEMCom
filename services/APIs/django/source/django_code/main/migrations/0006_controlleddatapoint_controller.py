# Generated by Django 2.2.5 on 2020-07-07 21:00

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0005_auto_20200707_2056'),
    ]

    operations = [
        migrations.AddField(
            model_name='controlleddatapoint',
            name='controller',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to='main.Controller'),
            preserve_default=False,
        ),
    ]
