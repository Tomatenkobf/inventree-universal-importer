import json
from django.contrib.contenttypes.models import ContentType
from common.models import Parameter, ParameterTemplate
from part.models import Part
from .parts import require


def apply(part, product, user, plugin, selected, overwrite):
    mapping = json.loads(plugin.get_setting("PARAMETER_MAP") or "{}")
    values = {
        int(mapping[name]): str(product.specifications[name])
        for name in selected
        if name in mapping and name in product.specifications
    }
    unknown = [name for name in selected if name not in mapping]
    if unknown:
        raise ValueError(
            "Map these specifications to parameter templates first: "
            + ", ".join(unknown)
        )
    ct = ContentType.objects.get_for_model(Part)
    for template_id, value in values.items():
        template = ParameterTemplate.objects.get(pk=template_id)
        if template.model_type_id != ct.pk:
            raise ValueError("Parameter template is not for parts")
        existing = Parameter.objects.filter(
            model_type=ct, model_id=part.pk, template=template
        ).first()
        if (
            existing
            and existing.data
            and "specifications." + template.name not in overwrite
        ):
            if existing.data != value:
                raise ValueError("Existing parameter is nonempty: " + template.name)
            continue
        require(user, "common.change_parameter" if existing else "common.add_parameter")
        param = existing or Parameter(
            model_type=ct, model_id=part.pk, template=template
        )
        param.data = value
        param.full_clean()
        param.save()


def gtin_parameter(part, product, user, plugin):
    template_id = int(plugin.get_setting("GTIN_TEMPLATE") or 0)
    if not template_id or not product.gtins:
        return
    ct = ContentType.objects.get_for_model(Part)
    template = ParameterTemplate.objects.get(pk=template_id, model_type=ct)
    existing = Parameter.objects.filter(
        model_type=ct, model_id=part.pk, template=template
    ).first()
    data = ", ".join(product.gtins)
    if existing:
        if existing.data != data:
            raise ValueError(
                "Existing GTIN parameter differs; resolve it explicitly in InvenTree"
            )
        return
    require(user, "common.add_parameter")
    param = Parameter(model_type=ct, model_id=part.pk, template=template, data=data)
    param.full_clean()
    param.save()
