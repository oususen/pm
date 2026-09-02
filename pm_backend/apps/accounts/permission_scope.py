from .models import Department


def collect_managed_department_ids(profile):
    """役職に応じた管理部署と、その配下部署のIDを返す。"""
    managed_department_ids = set()
    if profile.role == 'manager' and profile.division_id:
        managed_department_ids.add(profile.division_id)
    elif profile.role == 'chief' and profile.group_id:
        managed_department_ids.add(profile.group_id)
    elif profile.role == 'supervisor':
        if profile.team_id:
            managed_department_ids.add(profile.team_id)
        managed_department_ids.update(profile.supervisor_teams.values_list('id', flat=True))
    elif profile.role == 'leader':
        managed_department_ids.update(profile.leader_units.values_list('id', flat=True))

    pending_ids = managed_department_ids
    while pending_ids:
        child_ids = set(
            Department.objects.filter(parent_id__in=pending_ids).values_list('id', flat=True)
        ) - managed_department_ids
        if not child_ids:
            break
        managed_department_ids |= child_ids
        pending_ids = child_ids

    return managed_department_ids


def collect_effective_department_ids(profile):
    """本人の所属部署と、役職に応じて継承する管理範囲を返す。"""
    if not profile:
        return []

    ids = set()
    for field in ('department', 'division', 'group', 'team', 'unit'):
        dept = getattr(profile, field, None)
        if dept:
            ids.add(dept.id)
    ids.update(profile.leader_units.values_list('id', flat=True))
    ids.update(collect_managed_department_ids(profile))
    return list(ids)
