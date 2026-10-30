from company.models import Company, ManufacturerPart
from .parts import require


def apply(part, product, user, plugin):
    if not product.manufacturer or not product.mpn:
        raise ValueError(
            "Manufacturer and MPN are both required for a manufacturer part"
        )
    if len(product.mpn) > 100:
        raise ValueError("MPN exceeds 100 characters")
    companies = list(
        Company.objects.filter(name__iexact=product.manufacturer, is_manufacturer=True)[
            :2
        ]
    )
    if len(companies) > 1:
        raise ValueError(
            "Multiple manufacturers have this name; resolve the company records first"
        )
    if companies:
        company = companies[0]
    else:
        if not plugin.get_setting("ALLOW_MANUFACTURER_CREATE"):
            raise ValueError(
                "Manufacturer does not exist; administrator must enable manufacturer creation"
            )
        require(user, "company.add_company")
        company = Company(name=product.manufacturer, is_manufacturer=True)
        company.full_clean()
        company.save()
    if ManufacturerPart.objects.filter(
        part=part, manufacturer=company, MPN=product.mpn
    ).exists():
        return
    require(user, "company.add_manufacturerpart")
    record = ManufacturerPart(part=part, manufacturer=company, MPN=product.mpn)
    record.full_clean()
    record.save()
