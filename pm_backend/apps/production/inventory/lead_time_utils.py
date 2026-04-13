"""リードタイム解決の共通ユーティリティ。

業務ルール（統一）:
1. 投入LTは step.lead_time_days を使用し、0 は有効値としてそのまま採用する。
2. time_unit は LT 日数解決には影響しない（MINUTE/DAY 共通ルール）。
3. duration_min はサイクルタイム専用であり、LT 日数シフトには使わない。
4. line.lead_time_days は step.lead_time_days が未設定(None)のときのみフォールバック。
"""


def resolve_step_base_lead_days(step) -> int:
    """step の LT (日) を解決する。0 は有効値。None のときのみ line fallback。"""
    step_lt = getattr(step, 'lead_time_days', None)
    if step_lt is None:
        line = getattr(step, 'line', None)
        line_lt = int(getattr(line, 'lead_time_days', 0) or 0) if line else 0
        return max(line_lt, 0)
    return max(int(step_lt), 0)


def resolve_lead_days_for_step(step) -> int:
    """
    工程一段あたりの投入LT(日)を返す。

    - MINUTE / DAY ともに step.lead_time_days を使用（0 は有効値）
    - step.lead_time_days が None のときのみ line.lead_time_days にフォールバック
    - duration_min はサイクルタイム用途のため LT 計算には使用しない
    """
    return resolve_step_base_lead_days(step)
