from django.db.models import Q

from masters.models import BOMItem, Line, Process, Product, RoutingStep, Supplier
from masters.services.routing_service import build_effective_routing_q


def _build_purchase_line_name(supplier: Supplier) -> str:
    line_name = f"仕入:{supplier.supplier_code} {supplier.supplier_name}"
    return line_name[:50] if len(line_name) > 50 else line_name


def normalize_sourcing_type(value) -> str:
    normalized = str(value or '').strip().upper()
    return normalized if normalized in {'BUY', 'SUBCON', 'MAKE'} else ''


def normalize_supplier_type(supplier: Supplier | None) -> str:
    return str(getattr(supplier, 'supplier_type', 'both') or 'both').strip().lower()


def is_outsource_process(process: Process | None) -> bool:
    return bool(process and (process.process_code == 'G' or process.is_outsource))


def resolve_supplier_routing_process(
    supplier: Supplier | None,
    product: Product | None,
    line: Line | None = None,
    reference=None,
):
    """仕入先と加工後品目に一致する有効ルーティングから工程を一意に解決する。"""
    if not supplier or not product:
        return None

    target_line = line or resolve_purchase_line(supplier)
    supplier_filter = Q(supplier_id=supplier.id)
    if target_line:
        supplier_filter |= Q(line_id=target_line.id)

    steps = (
        RoutingStep.objects
        .filter(
            output_product_id=product.id,
            process_id__isnull=False,
        )
        .filter(build_effective_routing_q(reference, prefix='routing__'))
        .filter(supplier_filter)
        .select_related('process')
    )
    processes = {
        step.process_id: step.process
        for step in steps
        if step.process and (
            step.process.process_code == 'PURCHASE'
            or is_outsource_process(step.process)
        )
    }
    if len(processes) != 1:
        return None
    return next(iter(processes.values()))


def resolve_purchase_line(supplier: Supplier | None):
    if not supplier:
        return None
    line_obj, created = Line.objects.get_or_create(
        line_code=supplier.supplier_code,
        defaults={
            'line_name': _build_purchase_line_name(supplier),
            'line_type': 'PURCHASE',
            'is_active': True,
        }
    )
    if not created and line_obj.line_type != 'PURCHASE':
        line_obj.line_type = 'PURCHASE'
        line_obj.save(update_fields=['line_type'])
    return line_obj


def resolve_purchase_process(line: Line | None = None, create_if_missing: bool = False):
    if line:
        process = Process.objects.filter(line_id=line.id, process_code='PURCHASE').order_by('id').first()
        if process:
            return process

    process = Process.objects.filter(process_code='PURCHASE').order_by('id').first()
    if process or not (create_if_missing and line):
        return process

    return Process.objects.create(
        process_code='PURCHASE',
        process_name='購買',
        line=line,
        management_unit='DAY',
        is_active=False,
    )


def resolve_outsource_process(line: Line | None = None):
    base_qs = Process.objects.filter(Q(process_code='G') | Q(is_outsource=True)).order_by('id')
    if line:
        process = base_qs.filter(line_id=line.id).first()
        if process:
            return process
    return base_qs.first()


def _pick_best_bom_item(items, line: Line | None = None):
    if not items:
        return None

    def score(item):
        line_score = 2
        if line and item.line_id == line.id:
            line_score = 0
        elif item.line_id is None:
            line_score = 1

        process_score = 0 if item.process_id else 1
        return (line_score, process_score, -(item.id or 0))

    return sorted(items, key=score)[0]


def find_supplier_bom_item(
    supplier: Supplier | None,
    product: Product | None,
    line: Line | None = None,
    sourcing_type=None,
):
    if not supplier or not product:
        return None

    qs = BOMItem.objects.filter(
        supplier_id=supplier.id,
        child_product_id=product.id,
        bom__is_active=True,
        sourcing_type__in=['BUY', 'SUBCON'],
    ).select_related('process', 'line')

    normalized_sourcing = normalize_sourcing_type(sourcing_type)
    if normalized_sourcing:
        qs = qs.filter(sourcing_type=normalized_sourcing)

    return _pick_best_bom_item(list(qs), line=line)


def resolve_supplier_process(
    supplier: Supplier | None,
    line: Line | None = None,
    product: Product | None = None,
    preferred_process_id=None,
    sourcing_type=None,
    create_purchase_process: bool = False,
):
    target_line = line or resolve_purchase_line(supplier)
    preferred_process = (
        Process.objects.select_related('line').filter(id=preferred_process_id).first()
        if preferred_process_id else None
    )

    bom_item = find_supplier_bom_item(
        supplier=supplier,
        product=product,
        line=target_line,
        sourcing_type=sourcing_type,
    )
    resolved_sourcing = normalize_sourcing_type(sourcing_type)
    if not resolved_sourcing and bom_item:
        resolved_sourcing = normalize_sourcing_type(bom_item.sourcing_type)

    if resolved_sourcing == 'BUY':
        return resolve_purchase_process(target_line, create_if_missing=create_purchase_process)

    if resolved_sourcing == 'SUBCON':
        if bom_item and bom_item.process_id:
            return bom_item.process
        if preferred_process and is_outsource_process(preferred_process):
            return preferred_process
        return resolve_outsource_process(target_line)

    if preferred_process:
        return preferred_process

    supplier_type = normalize_supplier_type(supplier)
    if supplier_type == 'purchase':
        return resolve_purchase_process(target_line, create_if_missing=create_purchase_process)
    if supplier_type == 'outsource':
        return resolve_outsource_process(target_line)

    if target_line:
        line_processes = list(Process.objects.filter(line_id=target_line.id).order_by('id'))
        if len(line_processes) == 1:
            return line_processes[0]
        purchase_process = next((proc for proc in line_processes if proc.process_code == 'PURCHASE'), None)
        outsource_process = next((proc for proc in line_processes if is_outsource_process(proc)), None)
        if purchase_process or outsource_process:
            return purchase_process or outsource_process

    return (
        resolve_purchase_process(target_line, create_if_missing=create_purchase_process)
        or resolve_outsource_process(target_line)
    )
