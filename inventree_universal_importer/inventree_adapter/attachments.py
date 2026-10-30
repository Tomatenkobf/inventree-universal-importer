import io
import warnings
from PIL import Image
from common.models import Attachment
from django.core.files.base import ContentFile
from ..core.http import media_bytes
from ..core.normalization import safe_link
from .parts import require


def prepare(product, options, plugin):
    image = None
    pdf = None
    for field, urls in [
        ("image_url", product.image_urls),
        ("datasheet_url", product.datasheet_urls),
    ]:
        url = options.get(field)
        if url and url not in urls:
            raise ValueError("Select a media candidate from the preview")
        if url and not safe_link(url):
            raise ValueError("Invalid media URL")
    if options.get("image_url") or options.get("download_pdf"):
        if not plugin.get_setting("ALLOW_MEDIA"):
            raise ValueError("Media downloads are disabled")
        if not options.get("media_rights_confirmed"):
            raise ValueError("Confirm media usage rights before downloading")
    hosts = (plugin.get_setting("MEDIA_HOSTS") or "").split(",")
    if options.get("image_url"):
        data = media_bytes(options["image_url"], hosts)
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as im:
                if (
                    im.format not in ("JPEG", "PNG", "WEBP")
                    or im.width * im.height > 20_000_000
                ):
                    raise ValueError(
                        "Only JPEG/PNG/WebP up to 20 megapixels are accepted"
                    )
                im.verify()
            with Image.open(io.BytesIO(data)) as im:
                out = io.BytesIO()
                im.convert("RGB").save(out, format="JPEG", quality=90)
                image = out.getvalue()
    if options.get("download_pdf"):
        if not options.get("datasheet_url"):
            raise ValueError("Select a datasheet")
        pdf = media_bytes(options["datasheet_url"], hosts, 10_000_000)
        if not pdf.startswith(b"%PDF-"):
            raise ValueError("Datasheet is not a PDF")
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(pdf), strict=True)
        if reader.is_encrypted or not len(reader.pages):
            raise ValueError("Unreadable PDF")
        # Store as an attachment; never render or execute downloaded PDF content.
    return image, pdf


def apply(part, product, options, user, prepared, created_files):
    image, pdf = prepared
    if image:
        require(user, "part.change_part")
        if part.image:
            raise ValueError(
                "Image already exists; this release does not replace images"
            )
        part.image.save("product.jpg", ContentFile(image), save=False)
        created_files.append((part.image.storage, part.image.name))
        part.save()
    url = options.get("datasheet_url")
    if url:
        require(user, "common.add_attachment")
        if Attachment.objects.filter(
            model_type="part", model_id=part.pk, link=url
        ).exists():
            return
        attachment = Attachment(
            model_type="part",
            model_id=part.pk,
            link=url,
            comment=("Imported from " + product.source + "; see part provenance")[:250],
            upload_user=user,
        )
        if pdf:
            attachment.attachment.save("datasheet.pdf", ContentFile(pdf), save=False)
            created_files.append(
                (attachment.attachment.storage, attachment.attachment.name)
            )
        attachment.full_clean()
        attachment.save()
