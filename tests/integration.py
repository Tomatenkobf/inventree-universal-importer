"""Run with InvenTree manage.py test tests.integration (not plain pytest)."""

import io
import json
from unittest.mock import patch
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from django.core.cache import cache
from rest_framework.test import APIRequestFactory, force_authenticate
from part.models import Part, PartCategory
from company.models import ManufacturerPart
from common.models import Parameter, ParameterTemplate, Attachment
from plugin.models import PluginConfig
from inventree_universal_importer.plugin import UniversalImporterPlugin
from inventree_universal_importer.settings import SETTINGS
from inventree_universal_importer.core.models import Product
from inventree_universal_importer.inventree_adapter import importer, parts
from inventree_universal_importer.views import ImporterView


class IntegrationTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = get_user_model().objects.create_superuser(
            username="import_admin", email="admin@example.invalid", password="test-only"
        )
        self.plugin = UniversalImporterPlugin()
        self.values = {k: v["default"] for k, v in SETTINGS.items()}
        self.values.update(
            DEMO_ENABLED=True,
            OPENFOODFACTS_ENABLED=False,
            ALLOW_MANUFACTURER_CREATE=True,
        )
        self.plugin.get_setting = lambda key, *args, **kwargs: self.values[key]
        PluginConfig.objects.get_or_create(
            key=self.plugin.slug, defaults={"name": self.plugin.NAME, "active": True}
        )
        self.product = Product(
            name="Demo sensor",
            description="Sensor",
            manufacturer="Example Instruments",
            mpn="SENSOR-01",
            gtins=["4006381333931"],
            source="demo",
        ).finish()

    def preview(self, **options):
        defaults = {"fields": ["name", "description", "gtins", "manufacturer"]}
        defaults.update(options)
        return importer.preview(
            self.user,
            self.plugin,
            {"product": self.product.export(), "options": defaults},
        )

    def create(self, **options):
        p = self.preview(**options)
        return importer.commit(self.user, self.plugin, p["token"], True)

    def test_import_and_duplicates_and_idempotency(self):
        preview = self.preview()
        r = importer.commit(self.user, self.plugin, preview["token"], True)
        part = Part.objects.get(pk=r["part_id"])
        self.assertEqual(part.name, "Demo sensor")
        self.assertFalse(part.IPN)
        self.assertEqual(
            ManufacturerPart.objects.get(part=part).manufacturer.name,
            "Example Instruments",
        )
        self.assertEqual(
            parts.duplicates(self.product, plugin=self.plugin)[0]["id"], part.pk
        )
        second = importer.commit(self.user, self.plugin, preview["token"], True)
        self.assertTrue(second["replayed"])
        preview = self.preview()
        with self.assertRaisesRegex(ValueError, "Duplicate exists"):
            importer.commit(self.user, self.plugin, preview["token"], True)
        importer.commit(self.user, self.plugin, preview["token"], True, True)
        self.assertEqual(Part.objects.filter(name="Demo sensor").count(), 2)

    def test_no_automatic_stock(self):
        from stock.models import StockItem

        count = StockItem.objects.count()
        self.create()
        self.assertEqual(count, StockItem.objects.count())

    def test_permission_and_confirmation(self):
        preview = self.preview()
        with self.assertRaises(ValueError):
            importer.commit(self.user, self.plugin, preview["token"], False)
        user = get_user_model().objects.create_user(username="no_permissions")
        with self.assertRaises(PermissionDenied):
            importer.preview(user, self.plugin, {"product": self.product.export()})
        with self.assertRaises(PermissionDenied):
            importer.commit(user, self.plugin, preview["token"], True)

    def test_atomic_rollback(self):
        self.values["ALLOW_MANUFACTURER_CREATE"] = False
        count = Part.objects.count()
        with self.assertRaises(ValueError):
            self.create()
        self.assertEqual(count, Part.objects.count())

    def test_enrichment_and_stale_preview(self):
        part = Part.objects.get(pk=self.create()["part_id"])
        self.product.description = "New description"
        preview = self.preview(target_id=part.pk, fields=["description"])
        with self.assertRaisesRegex(ValueError, "Nonempty"):
            importer.commit(self.user, self.plugin, preview["token"], True)
        preview = self.preview(
            target_id=part.pk, fields=["description"], overwrite=["description"]
        )
        importer.commit(self.user, self.plugin, preview["token"], True)
        part.refresh_from_db()
        self.assertEqual(part.description, "New description")
        preview = self.preview(target_id=part.pk, fields=["description"])
        part.name = "Changed elsewhere"
        part.save()
        with self.assertRaisesRegex(ValueError, "changed since preview"):
            importer.commit(self.user, self.plugin, preview["token"], True)

    def test_parameter_category_mapping(self):
        ct = ContentType.objects.get_for_model(Part)
        template = ParameterTemplate.objects.create(name="Voltage", model_type=ct)
        gtin = ParameterTemplate.objects.create(name="GTIN", model_type=ct)
        category = PartCategory.objects.create(name="Sensors")
        self.values["PARAMETER_MAP"] = json.dumps({"Voltage": template.pk})
        self.values["GTIN_TEMPLATE"] = gtin.pk
        self.values["CATEGORY_MAP"] = json.dumps({"Sensors": category.pk})
        self.product.category = "Sensors"
        self.product.specifications = {"Voltage": "5 V"}
        result = self.create(
            fields=["name", "gtins", "specifications", "category"],
            specifications=["Voltage"],
        )
        part = Part.objects.get(pk=result["part_id"])
        self.assertEqual(part.category_id, category.pk)
        self.assertEqual(
            Parameter.objects.get(
                model_id=part.pk, model_type=ct, template=template
            ).data,
            "5 V",
        )
        self.assertEqual(
            Parameter.objects.get(model_id=part.pk, model_type=ct, template=gtin).data,
            "04006381333931",
        )

    def test_datasheet_link(self):
        self.product.datasheet_urls = ["https://example.com/sensor.pdf"]
        r = self.create(datasheet_url=self.product.datasheet_urls[0])
        self.assertTrue(
            Attachment.objects.filter(
                model_type="part",
                model_id=r["part_id"],
                link=self.product.datasheet_urls[0],
            ).exists()
        )

    def test_image_storage(self):
        from PIL import Image

        out = io.BytesIO()
        Image.new("RGB", (12, 12), "red").save(out, format="PNG")
        self.values["ALLOW_MEDIA"] = True
        self.product.image_urls = ["https://images.openfoodfacts.org/a.png"]
        with patch(
            "inventree_universal_importer.inventree_adapter.attachments.media_bytes",
            return_value=out.getvalue(),
        ):
            r = self.create(
                image_url=self.product.image_urls[0], media_rights_confirmed=True
            )
        part = Part.objects.get(pk=r["part_id"])
        self.assertTrue(part.image.storage.exists(part.image.name))
        part.image.delete()

    def test_api_search_and_permissions(self):
        factory = APIRequestFactory()
        view = ImporterView.as_view(plugin=self.plugin)
        request = factory.post(
            "/plugin/universal-importer/api/search/", {"text": "sensor"}, format="json"
        )
        self.assertIn(view(request, action="search").status_code, [401, 403])
        request = factory.post(
            "/plugin/universal-importer/api/search/", {"text": "sensor"}, format="json"
        )
        force_authenticate(request, user=self.user)
        response = view(request, action="search")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)

    def test_api_with_already_parsed_body(self):
        from rest_framework.request import Request
        from rest_framework.parsers import JSONParser
        from django.http.request import RawPostDataException

        raw = APIRequestFactory().post(
            "/plugin/universal-importer/api/config/", {}, format="json"
        )
        request = Request(raw, parsers=[JSONParser()])
        request.user = self.user
        self.assertEqual(request.data, {})
        # Some host versions cache the raw body during request setup.
        # Reproduce an already-consumed stream without that optional cache.
        if hasattr(raw, "_body"):
            del raw._body
        raw._read_started = True
        with self.assertRaises(RawPostDataException):
            _ = raw.body
        response = ImporterView(plugin=self.plugin).post(request, action="config")
        self.assertEqual(response.status_code, 200)

    def test_api_rejects_oversized_declared_body(self):
        raw = APIRequestFactory().post("/", {}, format="json")
        raw.META["CONTENT_LENGTH"] = "1100001"
        force_authenticate(raw, user=self.user)
        response = ImporterView.as_view(plugin=self.plugin)(raw, action="config")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error"], "Request too large")

    def test_ui_registration(self):
        from types import SimpleNamespace

        request = SimpleNamespace(user=self.user)
        with patch.object(
            self.plugin, "feature", return_value={"key": "universal-importer"}
        ):
            self.assertEqual(
                len(self.plugin.get_ui_panels(request, {"target_model": "part"})), 1
            )
            self.assertEqual(len(self.plugin.get_ui_dashboard_items(request, {})), 1)

    def test_actual_registry_urls_and_static_assets(self):
        from django.apps import apps
        from django.urls import reverse, resolve
        from django.contrib.staticfiles.storage import staticfiles_storage
        from plugin.staticfiles import copy_plugin_static_files
        from plugin.registry import registry

        self.assertTrue(apps.is_installed("inventree_universal_importer"))
        self.assertIsNotNone(registry.get_plugin(self.plugin.slug, active=None))
        url = reverse("plugin:universal-importer:api", kwargs={"action": "search"})
        self.assertEqual(resolve(url).kwargs["action"], "search")
        copy_plugin_static_files(self.plugin.slug)
        self.assertTrue(staticfiles_storage.exists("plugins/universal-importer/importer.js"))
        with staticfiles_storage.open("plugins/universal-importer/importer.js") as asset:
            self.assertIn(b"renderPanel", asset.read())

    def test_shared_rate_gate(self):
        from inventree_universal_importer.inventree_adapter.cache import SharedRateCache
        from inventree_universal_importer.models import RateGate

        a = SharedRateCache()
        b = SharedRateCache()
        self.assertTrue(a.add("upi:rate:test", True, 60))
        self.assertFalse(b.add("upi:rate:test", True, 60))
        RateGate.objects.filter(key="upi:rate:test").update(expires=0)
        self.assertTrue(b.add("upi:rate:test", True, 60))

    def test_background_job_ownership_execution_and_redaction(self):
        from inventree_universal_importer.jobs import enqueue, execute
        from inventree_universal_importer.models import ImportJob

        preview = self.preview()
        with patch("InvenTree.tasks.offload_task", return_value="task-id"):
            job = enqueue(
                self.user, [{"token": preview["token"], "confirm": True, "row": 4}]
            )
        self.assertNotIn("token", job["rows"][0])
        with patch("plugin.registry.registry.get_plugin", return_value=self.plugin):
            execute(job["id"])
        stored = ImportJob.objects.get(pk=job["id"])
        self.assertEqual(stored.status, "completed")
        self.assertNotIn("token", stored.rows[0])
        before = Part.objects.count()
        with patch("plugin.registry.registry.get_plugin", return_value=self.plugin):
            execute(job["id"])
        self.assertEqual(before, Part.objects.count())

    def test_corrupt_image_rejected_before_part_creation(self):
        self.values["ALLOW_MEDIA"] = True
        self.product.image_urls = ["https://images.openfoodfacts.org/a.png"]
        before = Part.objects.count()
        with patch(
            "inventree_universal_importer.inventree_adapter.attachments.media_bytes",
            return_value=b"not image",
        ):
            with self.assertRaises(Exception):
                self.create(
                    image_url=self.product.image_urls[0], media_rights_confirmed=True
                )
        self.assertEqual(before, Part.objects.count())

    def test_new_duplicate_after_preview_rejected(self):
        preview = self.preview()
        self.create()
        with self.assertRaisesRegex(ValueError, "Duplicate set changed"):
            importer.commit(self.user, self.plugin, preview["token"], True, True)

    def test_pdf_download_attachment(self):
        from pypdf import PdfWriter

        writer = PdfWriter()
        writer.add_blank_page(width=72, height=72)
        content = io.BytesIO()
        writer.write(content)
        self.values["ALLOW_MEDIA"] = True
        self.product.datasheet_urls = ["https://images.openfoodfacts.org/sensor.pdf"]
        with patch(
            "inventree_universal_importer.inventree_adapter.attachments.media_bytes",
            return_value=content.getvalue(),
        ):
            result = self.create(
                datasheet_url=self.product.datasheet_urls[0],
                download_pdf=True,
                media_rights_confirmed=True,
            )
        attachment = Attachment.objects.get(
            model_type="part", model_id=result["part_id"]
        )
        self.assertTrue(
            attachment.attachment.storage.exists(attachment.attachment.name)
        )
        self.assertEqual(attachment.link, self.product.datasheet_urls[0])
        attachment.attachment.delete()
