"""Approved imports on the existing InvenTree worker; no separate queue service."""

from datetime import timedelta
from django.contrib.auth import get_user_model
from django.core import signing
from django.utils import timezone
from .models import ImportJob
from .inventree_adapter import importer, parts


def enqueue(user, rows):
    if not isinstance(rows, list) or not 1 <= len(rows) <= 50:
        raise ValueError("Submit 1–50 explicitly reviewed rows per job")
    prepared = []
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValueError("Each row must be an object")
        if row.get("confirm") is not True:
            raise ValueError("Every queued row requires explicit confirmation")
        payload = signing.loads(row.get("token", ""), salt=importer.SALT, max_age=1800)
        if payload["user"] != user.pk:
            raise ValueError("Preview owner does not match")
        parts.require(
            user,
            "part.change_part"
            if payload["options"].get("target_id")
            else "part.add_part",
        )
        prepared.append(
            {
                "row": row.get("row", i + 1),
                "token": row["token"],
                "separate": row.get("separate") is True,
                "status": "pending",
            }
        )
    # Keep reports for 30 days; never retain tokens after completion.
    ImportJob.objects.filter(created__lt=timezone.now() - timedelta(days=30)).delete()
    job = ImportJob.objects.create(owner_id=user.pk, rows=prepared)
    from InvenTree.tasks import offload_task

    result = offload_task(
        "inventree_universal_importer.jobs.execute",
        str(job.pk),
        force_async=True,
        group="universal-importer",
    )
    if result is False:
        job.status = "queue_failed"
        job.save(update_fields=["status", "updated"])
    return public(job)


def public(job):
    return {
        "id": str(job.pk),
        "status": job.status,
        "rows": [
            {k: v for k, v in row.items() if k not in ("token", "separate")}
            for row in job.rows
        ],
    }


def execute(job_id):
    # Atomic claim prevents two workers processing the same job simultaneously.
    if not ImportJob.objects.filter(pk=job_id, status="queued").update(
        status="running", updated=timezone.now()
    ):
        return
    job = ImportJob.objects.get(pk=job_id)
    from plugin.registry import registry

    plugin = registry.get_plugin("universal-importer")
    user = get_user_model().objects.filter(pk=job.owner_id, is_active=True).first()
    for row in job.rows:
        if row["status"] == "imported":
            continue
        try:
            user = (
                get_user_model().objects.filter(pk=job.owner_id, is_active=True).first()
            )
            if not plugin or not plugin.get_setting("ENABLED") or not user:
                raise ValueError("Plugin or user is no longer active")
            result = importer.commit(user, plugin, row["token"], True, row["separate"])
            row.update(status="imported", part_id=result["part_id"])
        except Exception:
            # Avoid provider/ORM exception bodies or sensitive details in reports.
            row.update(
                status="failed",
                error="Import failed. Refresh the row preview and retry; check permissions, duplicates and field conflicts.",
            )
        row.pop("token", None)
        job.save(update_fields=["rows", "updated"])
    job.status = (
        "completed"
        if all(row["status"] == "imported" for row in job.rows)
        else "partial_failure"
    )
    job.save(update_fields=["status", "updated"])


def resume(user, job_id):
    job = ImportJob.objects.get(pk=job_id, owner_id=user.pk)
    # A stopped worker can be recovered; successful rows are never re-imported.
    if job.status == "running" and job.updated > timezone.now() - timedelta(minutes=10):
        raise ValueError("Job is still active; wait before attempting recovery")
    if job.status not in ("queued", "queue_failed", "running"):
        raise ValueError("Review failed rows again before submitting a new job")
    job.status = "queued"
    job.save(update_fields=["status", "updated"])
    from InvenTree.tasks import offload_task

    result = offload_task(
        "inventree_universal_importer.jobs.execute",
        str(job.pk),
        force_async=True,
        check_duplicates=False,
        group="universal-importer",
    )
    if result is False:
        job.status = "queue_failed"
        job.save(update_fields=["status", "updated"])
    return public(job)
