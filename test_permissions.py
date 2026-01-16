import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
django.setup()

from django.contrib.auth.models import User
from accounts.serializers import UserSerializer

# ユーザー000041を取得
user = User.objects.filter(username='000041').first()
if user:
    serializer = UserSerializer(user)
    data = serializer.data
    print('ユーザー:', user.username)
    print('ロール:', data.get('profile', {}).get('role'))
    print('部署:', data.get('profile', {}).get('department_name'))
    print('役職:', data.get('profile', {}).get('position'))

    # effective_permissionsを表示
    permissions = data.get('effective_permissions', [])
    print('\nEffective Permissions:')
    for perm in permissions:
        if perm.get('can_view') or perm.get('can_edit'):
            print(f'  {perm["resource"]}: view={perm["can_view"]}, edit={perm["can_edit"]}')
else:
    print('ユーザーが見つかりません')