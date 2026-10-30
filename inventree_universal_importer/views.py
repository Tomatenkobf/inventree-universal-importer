import json
from .inventree_adapter.cache import SharedRateCache

cache = SharedRateCache()
from django.core import signing
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.db import OperationalError, IntegrityError
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .core.models import Query, Product
from .core.search import Engine
from .core.csv_import import parse_csv
from .settings import provider_configs
from .inventree_adapter import parts, importer
from .inventree_adapter.version_detection import status, require_version


class ImporterView(APIView):
    permission_classes = [IsAuthenticated]
    plugin = None

    def post(self, request, action):
        try:
            require_version()
            if not self.plugin.get_setting("ENABLED"):
                return Response({"error": "Plugin is disabled"}, status=503)
            parts.require(request.user, "part.view_part")
            # Authentication may already have parsed the request stream.
            # Inspect its declared size without reading the raw body again.
            if int(request.META.get("CONTENT_LENGTH") or 0) > 1_100_000:
                raise ValueError("Request too large")
            data = request.data
            if not isinstance(data, dict):
                raise ValueError("JSON object required")
            if action == "config":
                from part.models import PartCategory

                return Response(
                    {
                        "compatibility": status(),
                        "categories": list(
                            PartCategory.objects.order_by("name").values("id", "name")
                        ),
                        "parameter_map": json.loads(
                            self.plugin.get_setting("PARAMETER_MAP") or "{}"
                        ),
                        "media_enabled": bool(self.plugin.get_setting("ALLOW_MEDIA")),
                    }
                )
            if action == "search":
                if not cache.add("upi:user:" + str(request.user.pk), True, timeout=2):
                    return Response(
                        {"error": "Please wait before searching again"}, status=429
                    )
                query = Query.parse(data)
                existing = parts.duplicates(
                    Product(
                        gtins=[query.gtin] if query.gtin else [],
                        manufacturer=query.manufacturer,
                        mpn=query.mpn,
                    ),
                    query.ipn,
                    self.plugin,
                )
                products, errors = Engine(
                    provider_configs(self.plugin),
                    cache,
                    int(self.plugin.get_setting("SEARCH_TIMEOUT")),
                ).search(query)
                result = []
                for p in products[:100]:
                    item = p.export()
                    item["existing"] = parts.duplicates(p, query.ipn, self.plugin)
                    result.append(item)
                return Response(
                    {"results": result, "existing": existing, "errors": errors}
                )
            if action == "preview":
                return Response(importer.preview(request.user, self.plugin, data))
            if action == "import":
                return Response(
                    importer.commit(
                        request.user,
                        self.plugin,
                        data.get("token", ""),
                        data.get("confirm"),
                        data.get("separate", False),
                    )
                )
            if action == "bulk":
                from .jobs import enqueue

                return Response(enqueue(request.user, data.get("rows")))
            if action == "job":
                from .models import ImportJob
                from .jobs import public

                return Response(
                    public(
                        ImportJob.objects.get(
                            pk=data.get("id"), owner_id=request.user.pk
                        )
                    )
                )
            if action == "resume":
                from .jobs import resume

                return Response(resume(request.user, data.get("id")))
            if action == "csv":
                return Response(
                    {"rows": parse_csv(data.get("csv", ""), data.get("mapping"))}
                )
            raise ValueError("Unknown action")
        except (
            ValueError,
            ValidationError,
            ObjectDoesNotExist,
            signing.BadSignature,
        ) as exc:
            if isinstance(exc, signing.BadSignature):
                message = "Preview expired or invalid; preview again"
            elif isinstance(exc, ObjectDoesNotExist):
                message = "Selected part, category or template no longer exists"
            else:
                message = str(exc)
            return Response({"error": message}, status=400)
        except (OperationalError, IntegrityError):
            return Response(
                {
                    "error": "Concurrent update or uniqueness conflict. Refresh the preview and retry."
                },
                status=409,
            )
        except OSError:
            return Response(
                {
                    "error": "Image, document or storage operation failed; no import was committed."
                },
                status=400,
            )
        except TypeError:
            return Response(
                {"error": "Invalid input type; check the submitted fields."}, status=400
            )
