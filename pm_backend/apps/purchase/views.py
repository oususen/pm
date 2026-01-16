from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import PurchasePlanLockSetting
from .serializers import PurchasePlanLockSettingSerializer


class PurchasePlanLockSettingView(APIView):
    def get(self, request):
        setting = PurchasePlanLockSetting.objects.first()
        if not setting:
            user = request.user if getattr(request, 'user', None) and request.user.is_authenticated else None
            setting = PurchasePlanLockSetting.objects.create(lock_days=0, updated_by=user)
        serializer = PurchasePlanLockSettingSerializer(setting)
        return Response(serializer.data)

    def post(self, request):
        raw_days = request.data.get('lock_days')
        try:
            lock_days = int(raw_days)
        except (TypeError, ValueError):
            return Response({'detail': 'lock_days must be integer'}, status=status.HTTP_400_BAD_REQUEST)
        if lock_days < 0:
            return Response({'detail': 'lock_days must be >= 0'}, status=status.HTTP_400_BAD_REQUEST)

        setting = PurchasePlanLockSetting.objects.first()
        user = request.user if getattr(request, 'user', None) and request.user.is_authenticated else None
        if not setting:
            setting = PurchasePlanLockSetting.objects.create(lock_days=lock_days, updated_by=user)
        else:
            setting.lock_days = lock_days
            setting.updated_by = user
            setting.save(update_fields=['lock_days', 'updated_at', 'updated_by'])

        serializer = PurchasePlanLockSettingSerializer(setting)
        return Response(serializer.data)
