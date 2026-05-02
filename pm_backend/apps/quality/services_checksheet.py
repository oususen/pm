import base64
import io
import json
import re
from datetime import date, datetime
from pathlib import Path

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from PIL import Image, ImageDraw, ImageFont

from .models_checksheet import (
    ProductChecksheetBatch,
    ProductChecksheetField,
    ProductChecksheetPhoto,
    ProductChecksheetRecord,
    ProductChecksheetTemplate,
)


FONT_CANDIDATES = {
    False: [
        r"C:\Windows\Fonts\meiryo.ttc",
        r"C:\Windows\Fonts\msgothic.ttc",
        r"C:\Windows\Fonts\YuGothR.ttc",
        "/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf",
        "/usr/share/fonts/truetype/takao-gothic/TakaoGothic.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ],
    True: [
        r"C:\Windows\Fonts\meiryob.ttc",
        r"C:\Windows\Fonts\msgothic.ttc",
        r"C:\Windows\Fonts\YuGothB.ttc",
        "/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf",
        "/usr/share/fonts/truetype/takao-gothic/TakaoGothic.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ],
}

TRUTHY = {"1", "true", "True", "on", True, 1}


def now_naive():
    return datetime.now()


def safe_filename(value: str) -> str:
    value = str(value or "").strip()
    value = re.sub(r"[\\/:*?\"<>|]+", "_", value)
    return value or "untitled"


def _duplicate_uploaded_file(uploaded_file):
    uploaded_file.seek(0)
    data = uploaded_file.read()
    return ContentFile(data, name=uploaded_file.name), data


def _pdf_first_page_to_png(file_bytes: bytes, stem: str):
    try:
        import fitz
    except ImportError as exc:
        raise RuntimeError("PDF台紙を使うには PyMuPDF のインストールが必要です。") from exc

    document = fitz.open(stream=file_bytes, filetype="pdf")
    page = document.load_page(0)
    matrix = fitz.Matrix(2, 2)
    pix = page.get_pixmap(matrix=matrix, alpha=False)
    image_bytes = pix.tobytes("png")
    document.close()
    return ContentFile(image_bytes, name=f"{safe_filename(stem)}.png"), pix.width, pix.height


def _normalize_image(file_bytes: bytes, stem: str):
    image = Image.open(io.BytesIO(file_bytes)).convert("RGB")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return ContentFile(buffer.getvalue(), name=f"{safe_filename(stem)}.png"), image.width, image.height


def create_background_assets(uploaded_pdf=None, uploaded_image=None):
    if uploaded_pdf:
        duplicated_pdf, pdf_bytes = _duplicate_uploaded_file(uploaded_pdf)
        background_content, width, height = _pdf_first_page_to_png(pdf_bytes, Path(uploaded_pdf.name).stem)
        return {
            "source_type": "pdf",
            "source_pdf": duplicated_pdf,
            "background_image": background_content,
            "background_width": width,
            "background_height": height,
        }
    if uploaded_image:
        duplicated_image, image_bytes = _duplicate_uploaded_file(uploaded_image)
        background_content, width, height = _normalize_image(image_bytes, Path(uploaded_image.name).stem)
        return {
            "source_type": "image",
            "source_image": duplicated_image,
            "background_image": background_content,
            "background_width": width,
            "background_height": height,
        }
    raise ValueError("台紙PDFまたは台紙画像が必要です。")


def active_template_for(line_id, process_id, product_id):
    return (
        ProductChecksheetTemplate.objects
        .select_related("line", "process", "product")
        .filter(
            line_id=line_id,
            process_id=process_id,
            product_id=product_id,
            is_active=True,
            status=ProductChecksheetTemplate.STATUS_APPROVED,
        )
        .order_by("-version", "-id")
        .first()
    )


def active_templates_for_product(product_id):
    """製品に紐づく全工程の承認済みテンプレートを返す（工程ごとに最新版のみ）"""
    from django.db.models import Max
    qs = (
        ProductChecksheetTemplate.objects
        .filter(
            product_id=product_id,
            is_active=True,
            status=ProductChecksheetTemplate.STATUS_APPROVED,
        )
        .values("line_id", "process_id")
        .annotate(max_version=Max("version"))
    )
    result = []
    for entry in qs:
        tmpl = (
            ProductChecksheetTemplate.objects
            .select_related("line", "process", "product")
            .filter(
                product_id=product_id,
                line_id=entry["line_id"],
                process_id=entry["process_id"],
                version=entry["max_version"],
                is_active=True,
                status=ProductChecksheetTemplate.STATUS_APPROVED,
            )
            .first()
        )
        if tmpl:
            result.append(tmpl)
    return result


def save_template_fields(template: ProductChecksheetTemplate, fields_payload):
    template.fields.all().delete()
    records = []
    for index, item in enumerate(fields_payload or []):
        key = str(item.get("key") or f"field_{index + 1}").strip() or f"field_{index + 1}"
        records.append(
            ProductChecksheetField(
                template=template,
                key=key,
                label=str(item.get("label") or key),
                field_type=str(item.get("field_type") or ProductChecksheetField.FIELD_TEXT),
                description=str(item.get("description") or ""),
                x=float(item.get("x") or 0),
                y=float(item.get("y") or 0),
                width=float(item.get("width") or 160),
                height=float(item.get("height") or 36),
                required=bool(item.get("required", False)),
                placeholder=str(item.get("placeholder") or ""),
                sort_order=index,
                show_label=bool(item.get("show_label", True)),
                text_direction=str(item.get("text_direction") or "horizontal"),
                counter_step=max(int(item.get("counter_step") or 1), 1),
            )
        )
    if records:
        ProductChecksheetField.objects.bulk_create(records)


def validate_record_required_fields(template: ProductChecksheetTemplate, payload, uploaded_files=None):
    uploaded_files = uploaded_files or {}
    missing = []
    for field in template.fields.all():
        if not field.required:
            continue
        value = payload.get(field.key)
        if field.field_type == ProductChecksheetField.FIELD_PHOTO:
            if field.key not in uploaded_files:
                missing.append(field.label)
        elif field.field_type == ProductChecksheetField.FIELD_PEN:
            if not value:
                missing.append(field.label)
        elif field.field_type == ProductChecksheetField.FIELD_CHECKBOX:
            if value not in TRUTHY:
                missing.append(field.label)
        else:
            if value in (None, "", []):
                missing.append(field.label)
    return missing


def normalize_responses(template: ProductChecksheetTemplate, payload):
    responses = {}
    for field in template.fields.all():
        raw = payload.get(field.key, "")
        value = raw in TRUTHY if field.field_type == ProductChecksheetField.FIELD_CHECKBOX else raw
        responses[field.key] = {
            "label": field.label,
            "field_type": field.field_type,
            "description": field.description,
            "value": value,
        }
    return responses


def prepare_batch(
    *,
    template,
    production_order=None,
    line,
    process,
    product,
    quantity,
    plan_date=None,
    lot_no="",
    operator_name="",
    source_context=None,
    user=None,
):
    quantity = int(quantity)
    filters = {
        "template": template,
        "production_order": production_order,
        "line": line,
        "process": process,
        "product": product,
        "lot_no": lot_no or "",
        "quantity": quantity,
        "status": ProductChecksheetBatch.STATUS_OPEN,
    }
    if plan_date is not None:
        filters["plan_date"] = plan_date
    batch = ProductChecksheetBatch.objects.filter(**filters).order_by("-id").first()
    if not batch:
        batch = ProductChecksheetBatch.objects.create(
            **filters,
            operator_name=operator_name or "",
            source_context=source_context or {},
            created_by=user if user and getattr(user, "is_authenticated", False) else None,
        )
        ProductChecksheetRecord.objects.bulk_create(
            [
                ProductChecksheetRecord(
                    batch=batch,
                    template=template,
                    sequence_no=seq,
                )
                for seq in range(1, quantity + 1)
            ]
        )
    return batch


def update_batch_status(batch: ProductChecksheetBatch):
    has_pending = batch.records.exclude(status__in=[ProductChecksheetRecord.STATUS_COMPLETED, ProductChecksheetRecord.STATUS_APPROVED]).exists()
    if has_pending:
        if batch.status != ProductChecksheetBatch.STATUS_OPEN:
            batch.status = ProductChecksheetBatch.STATUS_OPEN
            batch.completed_at = None
            batch.save(update_fields=["status", "completed_at", "updated_at"])
        return batch

    if batch.status != ProductChecksheetBatch.STATUS_COMPLETED:
        batch.status = ProductChecksheetBatch.STATUS_COMPLETED
        batch.completed_at = now_naive()
        batch.save(update_fields=["status", "completed_at", "updated_at"])
    return batch


def recalc_shipment_sequence(batch_id, planned_ship_date, shipment_unit_no):
    if not planned_ship_date or not shipment_unit_no:
        return
    records = ProductChecksheetRecord.objects.filter(
        batch_id=batch_id,
        planned_ship_date=planned_ship_date,
        shipment_unit_no=shipment_unit_no,
    ).order_by("sequence_no", "id")
    for index, record in enumerate(records, start=1):
        if record.shipment_sequence_no != index:
            ProductChecksheetRecord.objects.filter(id=record.id).update(shipment_sequence_no=index)


def parse_responses_json(raw_value):
    if isinstance(raw_value, dict):
        return raw_value
    if not raw_value:
        return {}
    try:
        value = json.loads(raw_value)
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def _find_font_path(bold=False):
    for candidate in FONT_CANDIDATES[bool(bold)]:
        if Path(candidate).exists():
            return candidate
    return None


def _font(size, bold=False):
    path = _find_font_path(bold=bold)
    if path:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            pass
    return ImageFont.load_default()


def _draw_centered_text(draw, center, text, font, fill):
    bbox = draw.textbbox((0, 0), text, font=font)
    width = bbox[2] - bbox[0]
    height = bbox[3] - bbox[1]
    draw.text((center[0] - width / 2, center[1] - height / 2), text, font=font, fill=fill)


def _draw_text_in_box(draw, field, text, fill="#111111"):
    if text in (None, "", False):
        return
    x, y = int(field.x), int(field.y)
    width, height = int(field.width), int(field.height)
    if field.text_direction == "vertical":
        font_size = max(min(width - 4, 28), 14)
        font = _font(font_size)
        current_y = y + 2
        center_x = x + width / 2
        for ch in str(text):
            bbox = draw.textbbox((0, 0), ch, font=font)
            ch_w = bbox[2] - bbox[0]
            ch_h = bbox[3] - bbox[1]
            if current_y + ch_h > y + height:
                break
            draw.text((center_x - ch_w / 2, current_y), ch, fill=fill, font=font)
            current_y += ch_h + 1
    else:
        draw.text((x + 4, y + 2), str(text), fill=fill, font=_font(max(min(height - 8, 28), 14)))


def _paste_photo(background, photo: ProductChecksheetPhoto, x, y, width, height):
    image = Image.open(photo.image.path).convert("RGB")
    image.thumbnail((max(width, 10), max(height, 10)))
    paste_x = x + max((width - image.width) // 2, 0)
    paste_y = y + max((height - image.height) // 2, 0)
    background.paste(image, (paste_x, paste_y))


def _paste_pen(background, data_url, x, y, width, height):
    if not data_url or "," not in str(data_url):
        return
    try:
        raw = base64.b64decode(str(data_url).split(",", 1)[1])
        image = Image.open(io.BytesIO(raw)).convert("RGBA")
        image = image.resize((max(width, 1), max(height, 1)))
        background.alpha_composite(image, (x, y))
    except Exception:
        return


def _draw_approval_stamp(draw, background, record, stamp_field=None):
    if stamp_field:
        left = int(stamp_field.x)
        top = int(stamp_field.y)
        stamp_size = int(max(stamp_field.width, stamp_field.height, 100))
    else:
        stamp_size = 160
        left = background.width - stamp_size - 24
        top = background.height - stamp_size - 24
    right = left + stamp_size
    bottom = top + stamp_size
    center = ((left + right) / 2, (top + bottom) / 2)
    color = (192, 37, 37, 220)
    draw.ellipse((left, top, right, bottom), outline=color, width=max(3, stamp_size // 36))
    draw.ellipse((left + 16, top + 16, right - 16, bottom - 16), outline=color, width=max(2, stamp_size // 90))
    _draw_centered_text(draw, (center[0], top + stamp_size * 0.22), "確認済", _font(max(16, stamp_size // 8), bold=True), color)
    _draw_centered_text(draw, center, record.supervisor_name or "-", _font(max(14, stamp_size // 8), bold=True), color)
    stamp_date = (record.approved_at or record.completed_at or record.created_at).strftime("%Y-%m-%d")
    _draw_centered_text(draw, (center[0], bottom - stamp_size * 0.18), stamp_date, _font(max(12, stamp_size // 10)), color)


def generate_template_preview_pdf(template: ProductChecksheetTemplate):
    if not template.background_image:
        return None
    background = Image.open(template.background_image.path).convert("RGBA")
    overlay = Image.new("RGBA", background.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    fields = list(template.fields.order_by("sort_order"))

    for field in fields:
        x, y = int(field.x), int(field.y)
        w, h = int(field.width), int(field.height)
        draw.rectangle((x, y, x + w, y + h), outline=(30, 64, 175, 140), width=2)
        fill = (230, 240, 255, 80)
        draw.rectangle((x + 1, y + 1, x + w - 1, y + h - 1), fill=fill)

        if field.show_label and field.label:
            font_size = max(min(h - 6, 18), 10)
            font = _font(font_size)
            label = field.label
            if field.required:
                label += " *"
            bbox = draw.textbbox((0, 0), label, font=font)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]
            tx = x + max((w - text_w) / 2, 2)
            ty = y + max((h - text_h) / 2, 1)
            draw.text((tx, ty), label, fill=(30, 64, 175, 200), font=font)

    background = Image.alpha_composite(background, overlay)
    output = io.BytesIO()
    background.convert("RGB").save(output, format="PDF", resolution=200.0)
    output.seek(0)
    return output


def generate_record_pdf(record: ProductChecksheetRecord):
    template = record.template
    if not template.background_image:
        return None
    background = Image.open(template.background_image.path).convert("RGBA")
    draw = ImageDraw.Draw(background)
    fields = list(template.fields.all())
    field_map = {field.key: field for field in fields}
    photo_map = {photo.field_key: photo for photo in record.photos.all()}
    stamp_field = next((f for f in fields if f.field_type == ProductChecksheetField.FIELD_SUPERVISOR_STAMP), None)

    for key, response in (record.responses_json or {}).items():
        field = field_map.get(key)
        if not field:
            continue
        value = response.get("value") if isinstance(response, dict) else response
        x, y = int(field.x), int(field.y)
        width, height = int(field.width), int(field.height)
        if field.field_type == ProductChecksheetField.FIELD_CHECKBOX:
            if value:
                font_size = max(min(height - 2, 26), 14)
                bbox = draw.textbbox((0, 0), "✓", font=_font(font_size, bold=True))
                mark_w = bbox[2] - bbox[0]
                mark_h = bbox[3] - bbox[1]
                draw.text((x + max((width - mark_w) / 2, 0), y + max((height - mark_h) / 2, 0) - 2), "✓", fill="#173624", font=_font(font_size, bold=True))
        elif field.field_type == ProductChecksheetField.FIELD_PHOTO:
            photo = photo_map.get(key)
            if photo:
                _paste_photo(background, photo, x, y, width, height)
        elif field.field_type == ProductChecksheetField.FIELD_PEN:
            _paste_pen(background, value, x, y, width, height)
        elif field.field_type == ProductChecksheetField.FIELD_SUPERVISOR_STAMP:
            continue
        else:
            _draw_text_in_box(draw, field, "" if value is None else str(value))

    _draw_approval_stamp(draw, background, record, stamp_field)

    output = io.BytesIO()
    background.convert("RGB").save(output, format="PDF", resolution=200.0)
    output.seek(0)

    batch = record.batch
    ship_date = record.planned_ship_date.isoformat() if record.planned_ship_date else date.today().isoformat()
    filename = (
        f"{safe_filename(batch.product.product_code)}_"
        f"{safe_filename(batch.lot_no or str(batch.id))}_"
        f"{record.sequence_no:04d}_{ship_date}_{record.id}.pdf"
    )
    storage_path = f"product_checksheets/approved_pdfs/{filename}"
    if record.generated_pdf:
        try:
            default_storage.delete(record.generated_pdf.name)
        except Exception:
            pass
    saved_path = default_storage.save(storage_path, ContentFile(output.read()))
    record.generated_pdf.name = saved_path
    record.save(update_fields=["generated_pdf", "updated_at"])
    return saved_path
