import pytest
from inventree_universal_importer.providers import REGISTRY, ProviderConfig
from inventree_universal_importer.core.models import Query
from inventree_universal_importer.core.normalization import gtin
from inventree_universal_importer.core.http import ProviderError


class HTTP:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []

    def json(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        value = self.responses.pop(0)
        if isinstance(value, Exception):
            raise value
        return value


def test_off():
    http = HTTP(
        {
            "status": 1,
            "product": {
                "code": "4006381333931",
                "product_name": "Test",
                "brands": "Brand",
                "image_front_url": "https://images.openfoodfacts.org/a.jpg",
                "quantity": "1 kg",
            },
        }
    )
    p = REGISTRY["openfoodfacts"](ProviderConfig(), http).search(
        Query(gtin=gtin("4006381333931"))
    )[0]
    assert p.gtins == ["04006381333931"] and p.quantity == "1 kg"
    assert p.image_licenses and p.metadata["provider_data"]["brands"] == "Brand"


def test_off_missing():
    assert (
        REGISTRY["openfoodfacts"](ProviderConfig(), HTTP({"status": 0})).search(
            Query(gtin=gtin("4006381333931"))
        )
        == []
    )


def test_icecat():
    http = HTTP(
        {
            "data": {
                "GeneralInfo": {
                    "Title": "PC",
                    "Brand": "ACME",
                    "BrandPartCode": "P1",
                    "GTIN": ["4006381333931"],
                    "Category": {"Name": {"Value": "Computers"}},
                },
                "Image": {"HighPic": "https://images.icecat.biz/a.jpg"},
                "FeaturesGroups": [
                    {
                        "Features": [
                            {
                                "Feature": {"Name": {"Value": "Memory"}},
                                "PresentationValue": "16 GB",
                            }
                        ]
                    }
                ],
            }
        }
    )
    p = REGISTRY["icecat"](ProviderConfig(username="test"), http).search(
        Query(manufacturer="ACME", mpn="P1")
    )[0]
    assert p.mpn == "P1" and p.specifications["Memory"] == "16 GB"
    assert http.calls[0][1]["params"]["ProductCode"] == "P1"


def test_eandb():
    http = HTTP(
        {
            "product": {
                "barcode": "4006381333931",
                "titles": {"de": "Schraube", "en": "Bolt"},
                "manufacturer": {"titles": {"en": "ACME"}},
                "images": [{"url": "https://example.com/a.jpg"}],
            }
        }
    )
    p = REGISTRY["eandb"](ProviderConfig(key="secret", language="de"), http).search(
        Query(gtin=gtin("4006381333931"))
    )[0]
    assert p.name == "Schraube" and p.manufacturer == "ACME"
    assert http.calls[0][1]["headers"]["Authorization"] == "Bearer secret"


def test_upc_paid_and_trial():
    for key, path in [("", "trial"), ("secret", "v1")]:
        http = HTTP(
            {
                "items": [
                    {
                        "title": "Bolt",
                        "upc": "036000291452",
                        "brand": "ACME",
                        "model": "B1",
                        "size": "M8",
                    }
                ]
            }
        )
        p = REGISTRY["upcitemdb"](ProviderConfig(key=key), http).search(
            Query(gtin=gtin("036000291452"))
        )[0]
        assert path in http.calls[0][0][1] and p.variants == {"size": "M8"}


def test_nexar():
    http = HTTP(
        {"access_token": "token"},
        {
            "data": {
                "supSearch": {
                    "results": [
                        {
                            "part": {
                                "id": "1",
                                "mpn": "A1",
                                "manufacturer": {"name": "ACME"},
                                "specs": [
                                    {
                                        "attribute": {"name": "Voltage"},
                                        "displayValue": "5 V",
                                    }
                                ],
                                "bestDatasheet": {"url": "https://example.com/a.pdf"},
                            }
                        }
                    ]
                }
            }
        },
    )
    p = REGISTRY["nexar"](ProviderConfig(key="client", secret="secret"), http).search(
        Query(mpn="A1")
    )[0]
    assert p.mpn == "A1" and p.specifications["Voltage"] == "5 V"
    assert http.calls[1][1]["json"]["variables"]["q"] == "A1"


@pytest.mark.parametrize("slug", ["icecat", "eandb", "nexar"])
def test_missing_credentials(slug):
    with pytest.raises(ProviderError, match="missing_credentials"):
        REGISTRY[slug](ProviderConfig(), HTTP()).search(
            Query(gtin="04006381333931", mpn="A1")
        )


@pytest.mark.parametrize(
    "code", ["timeout", "authentication_or_access_denied", "rate_limited"]
)
def test_failures(code):
    with pytest.raises(ProviderError, match=code):
        REGISTRY["openfoodfacts"](ProviderConfig(), HTTP(ProviderError(code))).search(
            Query(gtin="04006381333931")
        )


def test_demo():
    assert (
        REGISTRY["demo"](ProviderConfig(), HTTP())
        .search(Query(text="sensor"))[0]
        .metadata["synthetic"]
    )
