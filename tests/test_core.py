import pytest
from inventree_universal_importer.core.normalization import (
    gtin,
    barcode_for_api,
    safe_link,
)
from inventree_universal_importer.core.models import Query, Product
from inventree_universal_importer.core.matching import merge, equivalent
from inventree_universal_importer.core.csv_import import parse_csv, report_csv


@pytest.mark.parametrize(
    "value,expected",
    [
        ("4006381333931", "04006381333931"),
        ("036000291452", "00036000291452"),
        ("96385074", "00000096385074"),
        ("04006381333931", "04006381333931"),
    ],
)
def test_gtin(value, expected):
    assert gtin(value) == expected


@pytest.mark.parametrize(
    "value", ["4006381333932", "123", 12345678, "１２３４５６７８", "abcdefgh", ""]
)
def test_invalid_gtin(value):
    with pytest.raises(ValueError):
        gtin(value)


def test_barcode_roundtrip():
    for value in ["4006381333931", "036000291452", "96385074"]:
        assert gtin(barcode_for_api(gtin(value))) == gtin(value)


def test_query():
    with pytest.raises(ValueError):
        Query.parse({})
    with pytest.raises(ValueError):
        Query.parse({"text": "x" * 251})
    assert Query.parse({"manufacturer": " Acme "}).manufacturer == "Acme"


def test_mpn_case_and_manufacturer():
    a = Product(manufacturer="Acme", mpn="A-1")
    b = Product(manufacturer=" ACME ", mpn="a-1")
    assert equivalent(a, b)
    b.manufacturer = "Different"
    assert not equivalent(a, b)
    b.manufacturer = "Acme"
    b.mpn = "A1"
    assert not equivalent(a, b)


def test_no_name_merge():
    assert not equivalent(Product(name="Bolt"), Product(name="Bolt"))


@pytest.mark.parametrize(
    "key,value",
    [("packaging", "6 pack"), ("quantity", "2"), ("variants", {"size": "M8"})],
)
def test_variants_not_merged(key, value):
    a = Product(gtins=["04006381333931"])
    b = Product(gtins=a.gtins)
    setattr(b, key, value)
    assert not equivalent(a, b)


def test_conflicts_and_provenance():
    a = Product(name="One", source="a", gtins=["4006381333931"]).finish()
    b = Product(name="Two", source="b", gtins=["4006381333931"]).finish()
    merged = merge([a, b], Query(gtin=gtin("4006381333931")))
    assert len(merged) == 1 and merged[0].confidence == 0.99
    assert merged[0].conflicts["name"] == ["One", "Two"]
    assert len(merged[0].provenance["name"]) == 2 and len(merged[0].records) == 2
    assert not a.records


@pytest.mark.parametrize(
    "url",
    [
        "http://example.com",
        "javascript:alert(1)",
        "https://user:pass@example.com",
        "https://example.com:8080",
    ],
)
def test_bad_links(url):
    assert not safe_link(url)


def test_csv_preserves_zeroes_and_does_not_create_stock():
    rows = parse_csv("UPC,quantity,location\n036000291452,100,Bin A\n123,2,Bin B")
    assert rows[0]["query"]["gtin"] == "00036000291452"
    assert rows[0]["quantity"] == "100" and "error" in rows[1]


def test_csv_limits_and_mapping():
    with pytest.raises(ValueError):
        parse_csv("EAN,EAN\n1,2")
    with pytest.raises(ValueError):
        parse_csv("MPN\n" + "abc\n" * 201)
    assert (
        parse_csv("Item code\nSENSOR-01", {"Item code": "mpn"})[0]["query"]["mpn"]
        == "SENSOR-01"
    )


def test_csv_formula_escape():
    assert "'=bad" in report_csv([{"error": "=bad"}])
