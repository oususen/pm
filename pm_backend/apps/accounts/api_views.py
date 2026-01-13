from django.contrib.auth.models import User
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import viewsets
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.permissions import IsAdminUser
from django_filters.rest_framework import DjangoFilterBackend

from .models import (
    Department,
    UserProfile,
    DepartmentPermission,
    PositionPermission,
    DepartmentPositionPermission,
)
from .serializers import (
    DepartmentSerializer,
    UserSerializer,
    DepartmentPermissionSerializer,
    PositionPermissionSerializer,
    DepartmentPositionPermissionSerializer,
)


class DepartmentViewSet(viewsets.ModelViewSet):
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer
    permission_classes = [IsAdminUser]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['name', 'level']
    ordering_fields = ['display_id', 'name', 'level']
    ordering = ['display_id', 'id']


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.select_related('profile__department').prefetch_related('permissions')
    serializer_class = UserSerializer
    permission_classes = [IsAdminUser]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['is_active', 'is_staff', 'is_superuser']
    search_fields = ['username', 'email', 'first_name', 'last_name']
    ordering_fields = ['username', 'email', 'first_name', 'last_name']
    ordering = ['username']

    def get_queryset(self):
        return self.queryset


class DepartmentPermissionViewSet(viewsets.ModelViewSet):
    queryset = DepartmentPermission.objects.select_related('department')
    serializer_class = DepartmentPermissionSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        queryset = self.queryset
        department_id = self.request.query_params.get('department')
        if department_id:
            queryset = queryset.filter(department_id=department_id)
        return queryset

    @action(detail=False, methods=['post'], url_path='set')
    def set_permissions(self, request):
        department_id = request.data.get('department')
        permissions = request.data.get('permissions', [])
        if not department_id:
            return Response({'detail': 'department is required'}, status=400)

        DepartmentPermission.objects.filter(department_id=department_id).delete()
        records = []
        for perm in permissions:
            resource = perm.get('resource')
            if not resource:
                continue
            can_edit = bool(perm.get('can_edit'))
            can_view = bool(perm.get('can_view')) or can_edit
            records.append(
                DepartmentPermission(
                    department_id=department_id,
                    resource=resource,
                    can_view=can_view,
                    can_edit=can_edit,
                )
            )
        if records:
            DepartmentPermission.objects.bulk_create(records)
        serializer = self.get_serializer(
            DepartmentPermission.objects.filter(department_id=department_id),
            many=True,
        )
        return Response(serializer.data)


class PositionPermissionViewSet(viewsets.ModelViewSet):
    queryset = PositionPermission.objects.all()
    serializer_class = PositionPermissionSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        queryset = self.queryset
        position_name = self.request.query_params.get('position_name')
        if position_name:
            queryset = queryset.filter(position_name=position_name)
        return queryset

    @action(detail=False, methods=['post'], url_path='set')
    def set_permissions(self, request):
        position_name = (request.data.get('position_name') or '').strip()
        permissions = request.data.get('permissions', [])
        if not position_name:
            return Response({'detail': 'position_name is required'}, status=400)

        PositionPermission.objects.filter(position_name=position_name).delete()
        records = []
        for perm in permissions:
            resource = perm.get('resource')
            if not resource:
                continue
            can_edit = bool(perm.get('can_edit'))
            can_view = bool(perm.get('can_view')) or can_edit
            records.append(
                PositionPermission(
                    position_name=position_name,
                    resource=resource,
                    can_view=can_view,
                    can_edit=can_edit,
                )
            )
        if records:
            PositionPermission.objects.bulk_create(records)
        serializer = self.get_serializer(
            PositionPermission.objects.filter(position_name=position_name),
            many=True,
        )
        return Response(serializer.data)


class PositionListView(viewsets.ViewSet):
    permission_classes = [IsAdminUser]

    def list(self, request):
        names = set(
            UserProfile.objects.exclude(position='').values_list('position', flat=True)
        )
        names.update(
            PositionPermission.objects.exclude(position_name='').values_list(
                'position_name', flat=True
            )
        )
        return Response(sorted(names))


class DepartmentPositionPermissionViewSet(viewsets.ModelViewSet):
    queryset = DepartmentPositionPermission.objects.select_related('department')
    serializer_class = DepartmentPositionPermissionSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        queryset = self.queryset
        department_id = self.request.query_params.get('department')
        position_name = self.request.query_params.get('position_name')
        if department_id:
            queryset = queryset.filter(department_id=department_id)
        if position_name:
            queryset = queryset.filter(position_name=position_name)
        return queryset

    @action(detail=False, methods=['post'], url_path='set')
    def set_permissions(self, request):
        department_id = request.data.get('department')
        position_name = (request.data.get('position_name') or '').strip()
        permissions = request.data.get('permissions', [])
        if not department_id:
            return Response({'detail': 'department is required'}, status=400)
        if not position_name:
            return Response({'detail': 'position_name is required'}, status=400)

        DepartmentPositionPermission.objects.filter(
            department_id=department_id,
            position_name=position_name,
        ).delete()
        records = []
        for perm in permissions:
            resource = perm.get('resource')
            if not resource:
                continue
            can_edit = bool(perm.get('can_edit'))
            can_view = bool(perm.get('can_view')) or can_edit
            records.append(
                DepartmentPositionPermission(
                    department_id=department_id,
                    position_name=position_name,
                    resource=resource,
                    can_view=can_view,
                    can_edit=can_edit,
                )
            )
        if records:
            DepartmentPositionPermission.objects.bulk_create(records)
        serializer = self.get_serializer(
            DepartmentPositionPermission.objects.filter(
                department_id=department_id,
                position_name=position_name,
            ),
            many=True,
        )
        return Response(serializer.data)


class DepartmentPositionListView(viewsets.ViewSet):
    permission_classes = [IsAdminUser]

    def list(self, request):
        department_id = request.query_params.get('department')
        if not department_id:
            return Response({'detail': 'department is required'}, status=400)

        names = set(
            UserProfile.objects.filter(department_id=department_id)
            .exclude(position='')
            .values_list('position', flat=True)
        )
        names.update(
            DepartmentPositionPermission.objects.filter(department_id=department_id)
            .exclude(position_name='')
            .values_list('position_name', flat=True)
        )
        return Response(sorted(names))


class DivisionListView(viewsets.ViewSet):
    permission_classes = [IsAdminUser]

    def list(self, request):
        # 事業部レベルの部署のみを取得
        divisions = Department.objects.filter(level='division').order_by('display_id', 'name')
        serializer = DepartmentSerializer(divisions, many=True)
        return Response(serializer.data)


class GroupListView(viewsets.ViewSet):
    permission_classes = [IsAdminUser]

    def list(self, request):
        # parent_idが指定されている場合は、その事業部の子（係）のみを取得
        parent_id = request.query_params.get('parent')
        queryset = Department.objects.filter(level='group')
        if parent_id:
            queryset = queryset.filter(parent_id=parent_id)
        queryset = queryset.order_by('display_id', 'name')
        serializer = DepartmentSerializer(queryset, many=True)
        return Response(serializer.data)


class TeamListView(viewsets.ViewSet):
    permission_classes = [IsAdminUser]

    def list(self, request):
        # parent_idが指定されている場合は、その係の子（班）のみを取得
        parent_id = request.query_params.get('parent')
        queryset = Department.objects.filter(level='team')
        if parent_id:
            queryset = queryset.filter(parent_id=parent_id)
        queryset = queryset.order_by('display_id', 'name')
        serializer = DepartmentSerializer(queryset, many=True)
        return Response(serializer.data)
