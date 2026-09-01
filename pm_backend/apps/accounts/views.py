import logging

from django.contrib.auth import authenticate, get_user_model, login, logout
from django.middleware.csrf import get_token
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import (
    UnitLineMapping,
    UserProfile,
    UserPermission,
    DepartmentPermission,
    PositionPermission,
    DepartmentPositionPermission,
)
from .permission_scope import (
    collect_effective_department_ids,
    collect_managed_department_ids,
)

User = get_user_model()
IMPERSONATION_ORIGIN_SESSION_KEY = 'auth_impersonation_origin_user_id'
logger = logging.getLogger(__name__)

def _safe_get_profile(user):
    try:
        return user.profile
    except UserProfile.DoesNotExist:
        return None


def _profile_payload(user):
    try:
        profile = (
            UserProfile.objects.select_related('department', 'division', 'group', 'team', 'unit')
            .prefetch_related('supervisor_teams', 'leader_units')
            .filter(user_id=user.id)
            .first()
        )
    except Exception:
        return None

    if not profile:
        return None

    supervisor_teams = list(profile.supervisor_teams.all())
    leader_units = list(profile.leader_units.all())
    unit_lines = []
    if profile.unit_id:
        mappings = (
            UnitLineMapping.objects.select_related('line')
            .filter(unit_id=profile.unit_id)
            .order_by('-is_default', 'sort_order', 'id')
        )
        unit_lines = [
            {
                'id': mapping.id,
                'line_id': mapping.line_id,
                'line_code': mapping.line.line_code if mapping.line_id else '',
                'line_name': mapping.line.line_name if mapping.line_id else '',
                'sort_order': mapping.sort_order,
                'is_default': mapping.is_default,
            }
            for mapping in mappings
        ]

    return {
        'employee_code': profile.employee_code,
        'role': profile.role,
        'employment_type': profile.employment_type,
        'department': profile.department_id,
        'department_id': profile.department_id,
        'department_name': profile.department.name if profile.department_id else None,
        'division': profile.division_id,
        'division_id': profile.division_id,
        'division_name': profile.division.name if profile.division_id else None,
        'group': profile.group_id,
        'group_id': profile.group_id,
        'group_name': profile.group.name if profile.group_id else None,
        'team': profile.team_id,
        'team_id': profile.team_id,
        'team_name': profile.team.name if profile.team_id else None,
        'supervisor_teams': [team.id for team in supervisor_teams],
        'supervisor_team_names': [team.name for team in supervisor_teams],
        'leader_units': [unit.id for unit in leader_units],
        'leader_unit_names': [unit.name for unit in leader_units],
        'unit': profile.unit_id,
        'unit_id': profile.unit_id,
        'unit_name': profile.unit.name if profile.unit_id else None,
        'unit_lines': unit_lines,
        'joined_on': profile.joined_on.isoformat() if profile.joined_on else None,
    }

def _permissions_to_map(permissions):
    result = {}
    for perm in permissions:
        can_view = bool(getattr(perm, 'can_view', False))
        can_edit = bool(getattr(perm, 'can_edit', False))
        if not (can_view or can_edit):
            continue
        result[perm.resource] = {
            'resource': perm.resource,
            'can_view': can_view,
            'can_edit': can_edit,
        }
    return result


def _merge_permissions(base, overrides):
    for resource, perm in overrides.items():
        base[resource] = perm
    return base


def _collect_effective_department_ids(profile):
    return collect_effective_department_ids(profile)


def _build_effective_permissions(user):
    """
    ユーザーの有効権限を計算する。
    優先順位（低→高）:
    1. 部署のみの権限（DepartmentPermission）
    2. 役職のみの権限（PositionPermission）
    3. 部署×役職の権限（DepartmentPositionPermission）
    4. ユーザー個別権限（UserPermission）でオーバーライド
    """
    resources = [choice[0] for choice in UserPermission.RESOURCE_CHOICES]
    permission_map = {}

    if user.is_superuser:
        return [
            {'resource': resource, 'can_view': True, 'can_edit': True}
            for resource in resources
        ]

    profile = _safe_get_profile(user)
    position_name = profile.role if profile and profile.role else ''
    department_ids = _collect_effective_department_ids(profile)
    managed_department_ids = collect_managed_department_ids(profile) if profile else set()

    # 1. 部署のみの権限
    if department_ids:
        dept_permissions = DepartmentPermission.objects.filter(department_id__in=department_ids)
        permission_map = _merge_permissions(permission_map, _permissions_to_map(dept_permissions))

    # 2. 役職のみの権限
    if position_name:
        position_permissions = PositionPermission.objects.filter(position_name=position_name)
        permission_map = _merge_permissions(permission_map, _permissions_to_map(position_permissions))

    # 3. 部署×役職の権限
    if department_ids and position_name:
        combined_permissions = DepartmentPositionPermission.objects.filter(
            department_id__in=department_ids,
            position_name=position_name,
        )
        permission_map = _merge_permissions(permission_map, _permissions_to_map(combined_permissions))

    # 部署の長は、管理部署と配下部署に設定された一般権限を継承する。
    if managed_department_ids:
        staff_permissions = DepartmentPositionPermission.objects.filter(
            department_id__in=managed_department_ids,
            position_name='staff',
        )
        permission_map = _merge_permissions(permission_map, _permissions_to_map(staff_permissions))

    # 4. ユーザー個別権限
    user_permissions = []
    if hasattr(user, 'permissions'):
        user_permissions = list(user.permissions.all())
    if user_permissions:
        permission_map = _merge_permissions(permission_map, _permissions_to_map(user_permissions))

    if not permission_map:
        return []

    result = []
    for resource in resources:
        perm = permission_map.get(resource)
        if perm:
            result.append(perm)
    # RESOURCE_CHOICES 未反映のキーも返す（運用中の新規権限追加直後の取りこぼし防止）
    for resource, perm in permission_map.items():
        if resource not in resources:
            result.append(perm)
    return result


def _user_payload(user, request=None):
    return {
        'id': user.id,
        'username': user.get_username(),
        'email': user.email,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'is_staff': user.is_staff,
        'is_superuser': user.is_superuser,
        'profile': _profile_payload(user),
        'effective_permissions': _build_effective_permissions(user),
        'impersonation': _impersonation_payload(user, request),
    }


def _simple_user_payload(user):
    full_name = f'{user.last_name or ""} {user.first_name or ""}'.strip()
    return {
        'id': user.id,
        'username': user.get_username(),
        'first_name': user.first_name,
        'last_name': user.last_name,
        'display_name': full_name or user.get_username(),
    }


def _is_switch_admin_user(user):
    if not getattr(user, 'is_authenticated', False):
        return False
    username = str(user.get_username() or '').strip().lower()
    return username == 'admin'


def _get_origin_user_from_request(request):
    origin_id = request.session.get(IMPERSONATION_ORIGIN_SESSION_KEY)
    if not origin_id:
        return None
    return User.objects.filter(id=origin_id, is_active=True).first()


def _can_use_impersonation(request):
    return _is_switch_admin_user(request.user) or bool(_get_origin_user_from_request(request))


def _impersonation_payload(user, request=None):
    origin_user = _get_origin_user_from_request(request) if request is not None else None
    return {
        'can_switch': bool(_is_switch_admin_user(user) or origin_user),
        'active': bool(origin_user and origin_user.id != user.id),
        'origin_user': _simple_user_payload(origin_user) if origin_user else None,
    }


def _auth_response(request, user):
    token = get_token(request)
    return Response({'user': _user_payload(user, request), 'csrfToken': token})


def _request_ip(request):
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')


def _log_impersonation_event(request, action, actor_user, target_user=None, origin_user=None):
    logger.info(
        'impersonation action=%s actor=%s actor_id=%s target=%s target_id=%s origin=%s origin_id=%s ip=%s ua=%s',
        action,
        actor_user.get_username() if actor_user else '',
        actor_user.id if actor_user else '',
        target_user.get_username() if target_user else '',
        target_user.id if target_user else '',
        origin_user.get_username() if origin_user else '',
        origin_user.id if origin_user else '',
        _request_ip(request),
        request.META.get('HTTP_USER_AGENT', ''),
    )


@ensure_csrf_cookie
@api_view(['GET'])
@permission_classes([AllowAny])
def csrf(request):
    token = get_token(request)
    return Response({'csrfToken': token})


@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    username = (request.data.get('username') or '').strip()
    password = request.data.get('password') or ''

    if not username or not password:
        return Response(
            {'error': 'username and password are required'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user = authenticate(request, username=username, password=password)
    if not user:
        return Response(
            {'error': 'invalid credentials'},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    if not user.is_active:
        return Response(
            {'error': 'user is inactive'},
            status=status.HTTP_403_FORBIDDEN,
        )

    request.session.pop(IMPERSONATION_ORIGIN_SESSION_KEY, None)
    login(request, user)
    return _auth_response(request, user)


@api_view(['POST'])
@permission_classes([AllowAny])
def logout_view(request):
    logout(request)
    request.session.pop(IMPERSONATION_ORIGIN_SESSION_KEY, None)
    token = get_token(request)
    return Response({'ok': True, 'csrfToken': token})


@ensure_csrf_cookie
@api_view(['GET'])
@permission_classes([AllowAny])
def me(request):
    token = get_token(request)
    if request.user.is_authenticated:
        return Response(
            {
                'authenticated': True,
                'user': _user_payload(request.user, request),
                'csrfToken': token,
            }
        )

    return Response({'authenticated': False, 'user': None, 'csrfToken': token})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def switchable_users_view(request):
    if not _can_use_impersonation(request):
        return Response({'detail': '権限がありません。'}, status=status.HTTP_403_FORBIDDEN)

    current_user = request.user
    users = (
        User.objects.filter(is_active=True)
        .exclude(username__iexact='admin')
        .order_by('username')
    )
    return Response(
        {
            'current_user': _simple_user_payload(current_user),
            'impersonation': _impersonation_payload(current_user, request),
            'users': [_simple_user_payload(user) for user in users],
        }
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def switch_user_view(request):
    if not _can_use_impersonation(request):
        return Response({'detail': '権限がありません。'}, status=status.HTTP_403_FORBIDDEN)

    try:
        user_id = int(request.data.get('user_id') or 0)
    except (TypeError, ValueError):
        return Response({'detail': 'user_id が不正です。'}, status=status.HTTP_400_BAD_REQUEST)

    target_user = (
        User.objects.filter(id=user_id, is_active=True)
        .exclude(username__iexact='admin')
        .first()
    )
    if not target_user:
        return Response({'detail': '対象ユーザーが見つかりません。'}, status=status.HTTP_404_NOT_FOUND)

    origin_user = _get_origin_user_from_request(request)
    origin_user_id = origin_user.id if origin_user else request.user.id
    actor_user = origin_user if origin_user else request.user

    login(request, target_user)
    request.session[IMPERSONATION_ORIGIN_SESSION_KEY] = origin_user_id
    _log_impersonation_event(
        request,
        action='switch',
        actor_user=actor_user,
        target_user=target_user,
        origin_user=actor_user,
    )
    return _auth_response(request, target_user)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def switch_back_view(request):
    origin_user = _get_origin_user_from_request(request)
    if not origin_user:
        return Response({'detail': '切替元ユーザーが見つかりません。'}, status=status.HTTP_400_BAD_REQUEST)

    actor_user = request.user
    login(request, origin_user)
    request.session.pop(IMPERSONATION_ORIGIN_SESSION_KEY, None)
    _log_impersonation_event(
        request,
        action='switch_back',
        actor_user=origin_user,
        target_user=actor_user,
        origin_user=origin_user,
    )
    return _auth_response(request, origin_user)
