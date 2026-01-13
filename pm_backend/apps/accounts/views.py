from django.contrib.auth import authenticate, login, logout
from django.middleware.csrf import get_token
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import UserProfile


def _profile_payload(user):
    try:
        profile = (
            UserProfile.objects.select_related('department')
            .filter(user_id=user.id)
            .first()
        )
    except Exception:
        return None

    if not profile:
        return None

    return {
        'employee_code': profile.employee_code,
        'position': profile.position,
        'role': profile.role,
        'employment_type': profile.employment_type,
        'department_id': profile.department_id,
        'department_name': profile.department.name if profile.department_id else None,
        'division': profile.division,
        'group': profile.group,
        'team': profile.team,
        'joined_on': profile.joined_on.isoformat() if profile.joined_on else None,
    }


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
