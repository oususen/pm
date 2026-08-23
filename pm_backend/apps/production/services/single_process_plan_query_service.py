"""単独計画の参照系サービス"""
from rest_framework.response import Response

from production.models_singleproc_finished_entry import SingleProcFinishedEntry


def list_finished_entries(viewset, request, **deps):
    line_id = request.query_params.get('line')
    process_id = request.query_params.get('process')
    date_gte = request.query_params.get('plan_date__gte')
    date_lte = request.query_params.get('plan_date__lte')

    if not line_id or not process_id:
        return Response([])

    queryset = build_finished_entries_queryset(
        line_id=line_id,
        process_id=process_id,
        date_gte=date_gte,
        date_lte=date_lte,
    )
    return Response(serialize_finished_entries(queryset))


def build_finished_entries_queryset(*, line_id, process_id, date_gte=None, date_lte=None):
    queryset = SingleProcFinishedEntry.objects.filter(
        line_id=line_id,
        process_id=process_id,
    ).select_related('product')
    if date_gte:
        queryset = queryset.filter(plan_date__gte=date_gte)
    if date_lte:
        queryset = queryset.filter(plan_date__lte=date_lte)
    return queryset.order_by('plan_date', 'sequence_no')


def serialize_finished_entries(rows):
    return [
        {
            'plan_date': str(row.plan_date),
            'sequence_no': row.sequence_no,
            'product_id': row.product_id,
            'product_code': row.product.product_code if row.product else '',
            'product_name': row.product.product_name if row.product else '',
            'quantity': row.quantity,
        }
        for row in rows
    ]
