from django.contrib.auth.models import User
from django.db import transaction
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import viewsets
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend

from .models import (
    ApprovalRouteConfig,
    Department,
    UnitLineMapping,
    UserProfile,
    UserPermission,
    DepartmentPermission,
    PositionPermission,
    DepartmentPositionPermission,
    UserSmtpConfig,
    UserFavorite,
)
from .serializers import (
    DepartmentSerializer,
    UserSerializer,
    UserDetailSerializer,
    DepartmentPermissionSerializer,
    PositionPermissionSerializer,
    DepartmentPositionPermissionSerializer,
    UserSmtpConfigSerializer,
    UnitLineMappingSerializer,
    UserFavoriteSerializer,
    ApprovalRouteConfigSerializer,
)

class DepartmentViewSet(viewsets.ModelViewSet):
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['name', 'level']
    ordering_fields = ['display_id', 'name', 'level']
    ordering = ['display_id', 'id']


class UserViewSet(viewsets.ModelViewSet):
    queryset = (
        User.objects.select_related(
            'profile__department',
            'profile__division',
            'profile__group',
            'profile__team',
            'profile__unit',
        )
        .prefetch_related('permissions', 'profile__supervisor_teams', 'profile__leader_units')
    )
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['is_active', 'is_staff', 'is_superuser']
    search_fields = ['username', 'email', 'first_name', 'last_name']
    ordering_fields = ['username', 'email', 'first_name', 'last_name']
    ordering = ['username']

    def get_queryset(self):
        return self.queryset

    def get_serializer_class(self):
        if self.action in ('retrieve', 'create', 'update', 'partial_update'):
            return UserDetailSerializer
        return UserSerializer

    @action(detail=False, methods=['get', 'patch'], permission_classes=[])
    def me(self, request):
        user = request.user
        if request.method == 'GET':
            serializer = self.get_serializer(user)
            return Response(serializer.data)
        elif request.method == 'PATCH':
            serializer = self.get_serializer(user, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=400)


class DepartmentPermissionViewSet(viewsets.ModelViewSet):
    queryset = DepartmentPermission.objects.select_related('department')
    serializer_class = DepartmentPermissionSerializer
    permission_classes = [IsAuthenticated]

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
    permission_classes = [IsAuthenticated]

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
    permission_classes = [IsAuthenticated]

    def list(self, request):
        names = set(
            UserProfile.objects.exclude(role='').values_list('role', flat=True)
        )
        names.update(
            PositionPermission.objects.exclude(position_name='').values_list(
                'position_name', flat=True
            )
        )
        names.update(
            DepartmentPositionPermission.objects.exclude(position_name='').values_list(
                'position_name', flat=True
            )
        )
        names.update({'manager', 'chief', 'supervisor', 'leader', 'office_staff', 'staff'})
        return Response(sorted(names))


class DepartmentPositionPermissionViewSet(viewsets.ModelViewSet):
    queryset = DepartmentPositionPermission.objects.select_related('department')
    serializer_class = DepartmentPositionPermissionSerializer
    permission_classes = [IsAuthenticated]

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
    permission_classes = [IsAuthenticated]

    def list(self, request):
        department_id = request.query_params.get('department')
        if not department_id:
            return Response({'detail': 'department is required'}, status=400)

        names = set(
            UserProfile.objects.filter(department_id=department_id)
            .exclude(role='')
            .values_list('role', flat=True)
        )
        names.update(
            DepartmentPositionPermission.objects.filter(department_id=department_id)
            .exclude(position_name='')
            .values_list('position_name', flat=True)
        )
        names.update({'manager', 'chief', 'supervisor', 'leader', 'office_staff', 'staff'})
        return Response(sorted(names))


class DivisionListView(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request):
        # 事業部レベルの部署のみを取得
        divisions = Department.objects.filter(level='division').order_by('display_id', 'name')
        serializer = DepartmentSerializer(divisions, many=True)
        return Response(serializer.data)


class GroupListView(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

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
    permission_classes = [IsAuthenticated]

    def list(self, request):
        # parent_idが指定されている場合は、その係の子（班）のみを取得
        parent_id = request.query_params.get('parent')
        queryset = Department.objects.filter(level='team')
        if parent_id:
            queryset = queryset.filter(parent_id=parent_id)
        queryset = queryset.order_by('display_id', 'name')
        serializer = DepartmentSerializer(queryset, many=True)
        return Response(serializer.data)


class UnitListView(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request):
        # parent_idが指定されている場合は、その班の子（グループ）のみを取得
        parent_id = request.query_params.get('parent')
        queryset = Department.objects.filter(level='unit')
        if parent_id:
            queryset = queryset.filter(parent_id=parent_id)
        queryset = queryset.order_by('display_id', 'name')
        serializer = DepartmentSerializer(queryset, many=True)
        return Response(serializer.data)


class UnitLineMappingViewSet(viewsets.ModelViewSet):
    queryset = UnitLineMapping.objects.select_related('unit', 'line')
    serializer_class = UnitLineMappingSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['unit', 'line']
    ordering_fields = ['unit__display_id', 'unit__name', 'sort_order', 'id']
    ordering = ['unit__display_id', 'unit__name', '-is_default', 'sort_order', 'id']

    @action(detail=False, methods=['post'], url_path='set-for-line')
    def set_for_line(self, request):
        line_id = request.data.get('line')
        unit_ids = request.data.get('unit_ids', [])

        if not line_id:
            return Response({'detail': 'line is required'}, status=400)
        if unit_ids is None:
            unit_ids = []
        if not isinstance(unit_ids, list):
            return Response({'detail': 'unit_ids must be list'}, status=400)

        normalized_unit_ids = []
        for unit_id in unit_ids:
            try:
                normalized_unit_ids.append(int(unit_id))
            except (TypeError, ValueError):
                return Response({'detail': 'unit_ids must contain integers'}, status=400)

        valid_unit_ids = set(
            Department.objects.filter(level='unit', id__in=normalized_unit_ids).values_list('id', flat=True)
        )
        invalid_ids = [uid for uid in normalized_unit_ids if uid not in valid_unit_ids]
        if invalid_ids:
            return Response({'detail': f'invalid unit ids: {invalid_ids}'}, status=400)

        existing = UnitLineMapping.objects.filter(line_id=line_id)
        existing_by_unit = {m.unit_id: m for m in existing}
        requested_set = set(normalized_unit_ids)

        for unit_id in requested_set:
            if unit_id not in existing_by_unit:
                UnitLineMapping.objects.create(
                    unit_id=unit_id,
                    line_id=line_id,
                    sort_order=0,
                    is_default=False,
                )

        delete_ids = [m.id for uid, m in existing_by_unit.items() if uid not in requested_set]
        if delete_ids:
            UnitLineMapping.objects.filter(id__in=delete_ids).delete()

        serializer = self.get_serializer(
            UnitLineMapping.objects.filter(line_id=line_id).order_by('-is_default', 'sort_order', 'id'),
            many=True,
        )
        return Response(serializer.data)


class UserSmtpConfigViewSet(viewsets.ModelViewSet):
    queryset = UserSmtpConfig.objects.select_related('user')
    serializer_class = UserSmtpConfigSerializer
    permission_classes = [IsAdminUser]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['is_active', 'is_admin']
    search_fields = ['user__username', 'smtp_user', 'smtp_host']
    ordering = ['user__username']
    
    @action(detail=False, methods=['get'])
    def current_user(self, request):
        """現在のユーザーのSMTP設定を取得"""
        try:
            config = UserSmtpConfig.objects.get(user=request.user)
            serializer = self.get_serializer(config)
            return Response(serializer.data)
        except UserSmtpConfig.DoesNotExist:
            return Response({'detail': 'SMTP設定が見つかりません'}, status=404)


class UserFavoriteViewSet(viewsets.ModelViewSet):
    queryset = UserFavorite.objects.select_related('user')
    serializer_class = UserFavoriteSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['screen_key']
    ordering = ['screen_key', 'name', 'id']

    def get_queryset(self):
        user = self.request.user
        return self.queryset.filter(user=user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class ApprovalRouteConfigViewSet(viewsets.ModelViewSet):
    queryset = ApprovalRouteConfig.objects.prefetch_related(
        'creator_allowed_users',
        'creator_authorized_users',
        'creator_proxy_users',
        'reviewer1_allowed_users',
        'reviewer1_proxy_users',
        'reviewer2_allowed_users',
        'reviewer2_proxy_users',
        'approver_allowed_users',
        'approver_proxy_users',
    )
    serializer_class = ApprovalRouteConfigSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['item_key', 'item_name', 'note']
    ordering_fields = ['item_key', 'item_name', 'id']
    ordering = ['item_key', 'id']

    @action(detail=False, methods=['put'], url_path='bulk-save')
    def bulk_save(self, request):
        routes = request.data.get('routes')
        if not isinstance(routes, list):
            return Response({'detail': 'routes must be list'}, status=400)
        delete_ids = request.data.get('delete_ids', [])
        if delete_ids is None:
            delete_ids = []
        if not isinstance(delete_ids, list):
            return Response({'detail': 'delete_ids must be list'}, status=400)

        try:
            normalized_delete_ids = [int(route_id) for route_id in delete_ids]
        except (TypeError, ValueError):
            return Response({'detail': 'delete_ids must contain integers'}, status=400)

        item_keys = [(route.get('item_key') or '').strip() for route in routes if isinstance(route, dict)]
        if len(item_keys) != len(set(item_keys)):
            return Response({'detail': 'item_key must be unique'}, status=400)

        serializer = self.get_serializer(data=routes, many=True)
        serializer.is_valid(raise_exception=True)
        save_ids = [route.get('id') for route in serializer.validated_data if route.get('id')]
        delete_id_set = set(normalized_delete_ids)
        conflict_ids = sorted(delete_id_set.intersection(save_ids))
        if conflict_ids:
            return Response({'detail': f'cannot save and delete same ids: {conflict_ids}'}, status=400)

        for route in serializer.validated_data:
            route_id = route.get('id')
            item_key = route.get('item_key')
            duplicate = ApprovalRouteConfig.objects.filter(item_key=item_key).exclude(id__in=delete_id_set)
            if route_id:
                duplicate = duplicate.exclude(id=route_id)
            if duplicate.exists():
                return Response({'detail': f'item_key already exists: {item_key}'}, status=400)

        m2m_fields = [
            'creator_allowed_users',
            'creator_authorized_users',
            'creator_proxy_users',
            'reviewer1_allowed_users',
            'reviewer1_proxy_users',
            'reviewer2_allowed_users',
            'reviewer2_proxy_users',
            'approver_allowed_users',
            'approver_proxy_users',
        ]
        with transaction.atomic():
            for route in serializer.validated_data:
                route_id = route.pop('id', None)
                user_lists = {field: route.pop(field, []) for field in m2m_fields}
                if route_id:
                    obj, _ = ApprovalRouteConfig.objects.update_or_create(
                        id=route_id,
                        defaults=route,
                    )
                else:
                    obj, _ = ApprovalRouteConfig.objects.update_or_create(
                        item_key=route['item_key'],
                        defaults=route,
                    )
                for field, users in user_lists.items():
                    getattr(obj, field).set(users)

            if normalized_delete_ids:
                ApprovalRouteConfig.objects.filter(id__in=normalized_delete_ids).delete()
        return Response(self.get_serializer(self.get_queryset(), many=True).data)
