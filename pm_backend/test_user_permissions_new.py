import os
import sys
import django
from pathlib import Path

base_dir = Path(__file__).resolve().parent
apps_dir = base_dir / "apps"
sys.path.insert(0, str(base_dir))
sys.path.insert(0, str(apps_dir))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
django.setup()

from django.contrib.auth.models import User
from accounts.views import _build_effective_permissions

# ユーザー000041を取得
username = '000041'
user = User.objects.select_related('profile', 'profile__department').filter(username=username).first()
if not user:
    print(f'ユーザー {username} が見つかりません')
    sys.exit(1)

print(f'=== ユーザー: {user.username} ===')
profile = getattr(user, 'profile', None)
if profile:
    print(f'部署: {profile.department.name if profile.department else "なし"}')
    print(f'役職: {profile.position}')

print(f'\n=== 計算された権限 ===')
permissions = _build_effective_permissions(user)
for perm in permissions:
    if perm.get('can_view') or perm.get('can_edit'):
        print(f"  {perm['resource']}: view={perm['can_view']}, edit={perm['can_edit']}")
