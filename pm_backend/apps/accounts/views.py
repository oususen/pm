from django.contrib.auth import authenticate, login, logout
from django.middleware.csrf import get_token
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

try:
    from proposals.models import Employee, EmployeePermission
except Exception:
    Employee = None
    EmployeePermission = None


def _employee_payload(user):
    if not Employee:
        return None

    try:
        employee = (
            Employee.objects.select_related('department')
            .filter(user_id=user.id, is_active=True)
            .first()
        )
    except Exception:
        return None

    if not employee:
        return None

    permissions = []
    if EmployeePermission:
        try:
            permissions = list(
                EmployeePermission.objects.filter(employee_id=employee.id).values(
                    'resource',
                    'can_view',
                    'can_edit',
                )
            )
        except Exception:
            permissions = []

    return {
        'id': employee.id,
        'code': employee.code,
        'name': employee.name,
        'email': employee.email,
        'position': employee.position,
        'role': employee.role,
        'department': employee.department.name if employee.department_id else None,
        'division': employee.division,
        'group': employee.group_name,
        'team': employee.team_name,
        'employment_type': employee.employment_type,
        'permissions': permissions,
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
        'employee': _employee_payload(user),
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
