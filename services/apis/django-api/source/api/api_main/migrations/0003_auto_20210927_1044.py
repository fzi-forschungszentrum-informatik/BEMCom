# Generated by Django 3.1.5 on 2021-09-27 10:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("api_main", "0002_auto_20210904_2242")]

    operations = [
        migrations.AlterField(
            model_name="datapoint",
            name="short_name",
            field=models.TextField(
                blank=True,
                default=None,
                help_text="A short name to identify the datapoint.",
                null=True,
                unique=True,
            ),
        )
    ]
