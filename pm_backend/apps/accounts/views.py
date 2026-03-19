from django.contrib.auth import authenticate, login, logout
from django.middleware.csrf import get_token
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import (
    UnitLineMapping,
    UserProfile,
    UserPermission,
    DepartmentPermission,
    PositionPermission,
    DepartmentPositionPermission,
)


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

    profile = getattr(user, 'profile', None)
    department_id = profile.department_id if profile else None
    position_name = profile.role if profile and profile.role else ''

    # 1. 部署のみの権限
    if department_id:
        dept_permissions = DepartmentPermission.objects.filter(department_id=department_id)
        permission_map = _merge_permissions(permission_map, _permissions_to_map(dept_permissions))

    # 2. 役職のみの権限
    if position_name:
        position_permissions = PositionPermission.objects.filter(position_name=position_name)
        permission_map = _merge_permissions(permission_map, _permissions_to_map(position_permissions))

    # 3. 部署×役職の権限
    if department_id and position_name:
        combined_permissions = DepartmentPositionPermission.objects.filter(
            department_id=department_id,
            position_name=position_name,
        )
        permission_map = _merge_permissions(permission_map, _permissions_to_map(combined_permissions))

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
    return result


def _user_payload(user):
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
    }


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

    login(request, user)
    token = get_token(request)
    return Response({'user': _user_payload(user), 'csrfToken': token})


@api_view(['POST'])
@permission_classes([AllowAny])
def logout_view(request):
    logout(request)
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
                'user': _user_payload(request.user),
                'csrfToken': token,
            }
        )

    return Response({'authenticated': False, 'user': None, 'csrfToken': token})
