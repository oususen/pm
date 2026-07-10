from django.db.models import Q


ROLE_RANK = {
    'staff': 0,
    'office_staff': 0,
    'leader': 1,
    'supervisor': 2,
    'chief': 3,
    'manager': 4,
    'admin': 5,
}


def get_role_rank(role):
    return ROLE_RANK.get(str(role or '').strip(), 0)


def get_profile_role(profile):
    return str(getattr(profile, 'role', '') or '').strip()


def get_profile(user):
    try:
        return user.profile
    except Exception:
        return None


def role_at_least(profile, minimum_role):
    return get_role_rank(get_profile_role(profile)) >= get_role_rank(minimum_role)


def get_assigned_team_ids(profile):
    if not profile:
        return set()
    team_ids = set()
    team_id = getattr(profile, 'team_id', None)
    if team_id:
        team_ids.add(team_id)
    supervisor_teams = getattr(profile, 'supervisor_teams', None)
    if supervisor_teams is not None:
        team_ids.update(supervisor_teams.values_list('id', flat=True))
    return team_ids


def get_assigned_unit_ids(profile):
    if not profile:
        return set()
    unit_ids = set()
    unit_id = getattr(profile, 'unit_id', None)
    if unit_id:
        unit_ids.add(unit_id)
    leader_units = getattr(profile, 'leader_units', None)
    if leader_units is not None:
        unit_ids.update(leader_units.values_list('id', flat=True))
    return unit_ids


def can_act_as_leader(profile, unit_id):
    return bool(unit_id) and role_at_least(profile, 'leader') and unit_id in get_assigned_unit_ids(profile)


def can_act_as_supervisor(profile, team_id):
    return bool(team_id) and role_at_least(profile, 'supervisor') and team_id in get_assigned_team_ids(profile)


def can_act_as_chief(profile, group_id):
    return bool(group_id) and role_at_least(profile, 'chief') and getattr(profile, 'group_id', None) == group_id


def can_act_as_manager(profile, division_id):
    return bool(division_id) and role_at_least(profile, 'manager') and getattr(profile, 'division_id', None) == division_id


def _prefixed(field_name, prefix='profile__'):
    return f'{prefix}{field_name}' if prefix else field_name


def build_leader_role_q(unit_id, prefix='profile__'):
    return (
        Q(**{_prefixed('role', prefix): 'leader', _prefixed('leader_units', prefix): unit_id})
        | Q(**{_prefixed('role', prefix): 'leader', _prefixed('unit_id', prefix): unit_id})
        | Q(**{_prefixed('role', prefix): 'supervisor', _prefixed('leader_units', prefix): unit_id})
        | Q(**{_prefixed('role', prefix): 'supervisor', _prefixed('unit_id', prefix): unit_id})
        | Q(**{_prefixed('role', prefix): 'chief', _prefixed('leader_units', prefix): unit_id})
        | Q(**{_prefixed('role', prefix): 'chief', _prefixed('unit_id', prefix): unit_id})
        | Q(**{_prefixed('role', prefix): 'manager', _prefixed('leader_units', prefix): unit_id})
        | Q(**{_prefixed('role', prefix): 'manager', _prefixed('unit_id', prefix): unit_id})
    )


def build_supervisor_role_q(team_id, prefix='profile__'):
    return (
        Q(**{_prefixed('role', prefix): 'supervisor', _prefixed('supervisor_teams', prefix): team_id})
        | Q(**{_prefixed('role', prefix): 'supervisor', _prefixed('team_id', prefix): team_id})
        | Q(**{_prefixed('role', prefix): 'chief', _prefixed('supervisor_teams', prefix): team_id})
        | Q(**{_prefixed('role', prefix): 'chief', _prefixed('team_id', prefix): team_id})
        | Q(**{_prefixed('role', prefix): 'manager', _prefixed('supervisor_teams', prefix): team_id})
        | Q(**{_prefixed('role', prefix): 'manager', _prefixed('team_id', prefix): team_id})
    )


def build_chief_role_q(group_id, prefix='profile__'):
    return (
        Q(**{_prefixed('role', prefix): 'chief', _prefixed('group_id', prefix): group_id})
        | Q(**{_prefixed('role', prefix): 'manager', _prefixed('group_id', prefix): group_id})
    )
