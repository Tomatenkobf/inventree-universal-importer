import uuid
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name="RateGate",
            fields=[
                (
                    "key",
                    models.CharField(max_length=120, primary_key=True, serialize=False),
                ),
                ("expires", models.FloatField(default=0)),
            ],
        ),
        migrations.CreateModel(
            name="ImportJob",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        primary_key=True,
                        default=uuid.uuid4,
                        editable=False,
                        serialize=False,
                    ),
                ),
                ("owner_id", models.PositiveIntegerField(db_index=True)),
                ("status", models.CharField(max_length=20, default="queued")),
                ("rows", models.JSONField(default=list)),
                ("created", models.DateTimeField(auto_now_add=True)),
                ("updated", models.DateTimeField(auto_now=True)),
            ],
        ),
    ]
