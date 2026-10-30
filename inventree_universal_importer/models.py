"""Plugin-owned tables only. No InvenTree core schema modifications."""

import uuid
from django.db import models


class RateGate(models.Model):
    key = models.CharField(max_length=120, primary_key=True)
    expires = models.FloatField(default=0)


class ImportJob(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner_id = models.PositiveIntegerField(db_index=True)
    status = models.CharField(max_length=20, default="queued")
    rows = models.JSONField(default=list)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
