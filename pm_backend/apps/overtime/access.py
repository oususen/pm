from django.contrib.auth import get_user_model


User = get_user_model()

SELF_ONLY_APPLICATION_TYPES = {'overtime', 'holiday'}


def get_user_role(user):
    try:
        return user.profile.role
    except Exception:
        return 'staff'


def get_proxy_applicant_queryset(user):
    qs = User.objects.filter(is_active=True).select_related('profile')
    role = get_user_role(user)

    try:
        profile = user.profile
    except Exception:
        return qs.filter(id=user.id)

    if role == 'supervisor':
        team_ids = set()
        if profile.team_id:
            team_ids.add(profile.team_id)
        team_ids.update(profile.supervisor_teams.values_list('id', flat=True))
        if not team_ids:
            return qs.filter(id=user.id)
        return qs.filter(profile__team_id__in=team_ids).distinct()

    if role == 'leader':
        unit_ids = set()
        if profile.unit_id:
            unit_ids.add(profile.unit_id)
        unit_ids.update(profile.leader_units.values_list('id', flat=True))
        if not unit_ids:
            return qs.filter(id=user.id)
        return qs.filter(profile__unit_id__in=unit_ids).distinct()

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
    if get_user_role(user) not in ('leader', 'supervisor'):
        return False
    return get_proxy_applicant_queryset(user).filter(id=applicant.id).exists()


def can_manage_application(user, application):
    if not user or not getattr(user, 'is_authenticated', False):
        return False
    if application.applicant_id == user.id:
        return True
    if application.created_by_id and application.created_by_id == user.id:
        return True
    return False
