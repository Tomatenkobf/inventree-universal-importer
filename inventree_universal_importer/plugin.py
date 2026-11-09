from plugin import InvenTreePlugin
from plugin.mixins import AppMixin, SettingsMixin, UrlsMixin, UserInterfaceMixin
from .settings import SETTINGS


class UniversalImporterPlugin(
    AppMixin, SettingsMixin, UrlsMixin, UserInterfaceMixin, InvenTreePlugin
):
    NAME = "Universal Product Importer"
    SLUG = "universal-importer"
    TITLE = "Universal Product Importer"
    DESCRIPTION = (
        "Review products from multiple databases before importing or enriching parts"
    )
    VERSION = "0.1.0rc3"
    MIN_VERSION = "1.5.6"
    MAX_VERSION = "1.7.0"
    SETTINGS = SETTINGS

    def __init__(self):
        super().__init__()
        import logging
        from .inventree_adapter.version_detection import status

        compatibility = status()
        if compatibility["warning"]:
            logging.getLogger(__name__).warning(
                "Universal importer compatibility: %s", compatibility["warning"]
            )

    def setup_urls(self):
        from django.urls import path
        from .views import ImporterView

        return [
            path("api/<str:action>/", ImporterView.as_view(plugin=self), name="api")
        ]

    def feature(self):
        from django.urls import reverse

        return {
            "key": "universal-importer",
            "title": self.TITLE,
            "icon": "ti:barcode",
            "source": self.plugin_static_file("importer.js:renderPanel"),
            "context": {
                "endpoint": reverse(
                    "plugin:universal-importer:api", kwargs={"action": "search"}
                ).replace("search/", "")
            },
        }

    def get_ui_panels(self, request, context, **kwargs):
        if not request.user.has_perm("part.view_part"):
            return []
        return (
            [self.feature()]
            if context.get("target_model") in ("part", "partcategory")
            else []
        )

    def get_ui_dashboard_items(self, request, context, **kwargs):
        if not request.user.has_perm("part.view_part"):
            return []
        feature = self.feature()
        feature["options"] = {"width": 6, "height": 6}
        return [feature]

    def get_admin_context(self):
        from .inventree_adapter.version_detection import status

        return status()

    def get_ui_routes(self, request, context, **kwargs):
        if not request.user.has_perm("part.view_part"):
            return []
        feature = self.feature()
        feature["options"] = {"path": "import"}
        return [feature]

    def get_ui_navigation_items(self, request, context, **kwargs):
        from packaging.version import Version
        from InvenTree.version import INVENTREE_SW_VERSION

        if Version(INVENTREE_SW_VERSION) < Version(
            "1.6.0"
        ) or not request.user.has_perm("part.view_part"):
            return []
        return [
            {
                "key": "universal-importer-nav",
                "title": self.TITLE,
                "icon": "ti:barcode",
                "options": {"url": "plugin/universal-importer/import"},
            }
        ]
