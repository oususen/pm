from django.contrib.auth import get_user_model

from accounts.role_utils import can_act_as_leader, can_act_as_supervisor, get_profile, get_profile_role


User = get_user_model()

SELF_ONLY_APPLICATION_TYPES = {'overtime', 'holiday'}


def get_user_role(user):
    profile = get_profile(user)
    return get_profile_role(profile) or 'staff'


def get_proxy_applicant_queryset(user):
    qs = User.objects.filter(is_active=True).select_related('profile')
    role = get_user_role(user)

    profile = get_profile(user)
    if not profile:
        return qs.filter(id=user.id)

    team_ids = set()
    unit_ids = set()

    if role in ('supervisor', 'chief', 'manager'):
        if getattr(profile, 'team_id', None):
            team_ids.add(profile.team_id)
        team_ids.update(profile.supervisor_teams.values_list('id', flat=True))

    if role in ('leader', 'supervisor', 'chief', 'manager'):
        if getattr(profile, 'unit_id', None):
            unit_ids.add(profile.unit_id)
        unit_ids.update(profile.leader_units.values_list('id', flat=True))

    if team_ids or unit_ids:
        result = qs.none()
        if team_ids:
            result = result | qs.filter(profile__team_id__in=team_ids)
        if unit_ids:
            result = result | qs.filter(profile__unit_id__in=unit_ids)
        return result.distinct()

    return qs.filter(id=user.id)


def can_apply_for(user, applicant, application_type):
    if not user or not getattr(user, 'is_authenticated', False):
        return False
    if not applicant:
        return False
    if applicant.id == user.id:
        return True
    if application_type in SELF_ONLY_APPLICATION_TYPES:
        return False
    profile = get_profile(user)
    applicant_profile = get_profile(applicant)
    if applicant_profile:
        if can_act_as_supervisor(profile, getattr(applicant_profile, 'team_id', None)):
            return True
        if can_act_as_leader(profile, getattr(applicant_profile, 'unit_id', None)):
            return True
    return get_proxy_applicant_queryset(user).filter(id=applicant.id).exists()


def can_manage_application(user, application):
    if not user or not getattr(user, 'is_authenticated', False):
        return False
    if application.applicant_id == user.id:
        return True
    if application.created_by_id and application.created_by_id == user.id:
        return True
    return False
