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
from accounts.models import UserProfile, DepartmentPositionPermission, UserPermission

# ユーザー000041を取得
username = '000041'
user = User.objects.filter(username=username).first()
if not user:
    print(f'ユーザー {username} が見つかりません')
    sys.exit(1)

print(f'=== ユーザー: {user.username} ===')
print(f'is_superuser: {user.is_superuser}')
print(f'is_staff: {user.is_staff}')

# プロファイル確認
try:
    profile = UserProfile.objects.select_related('department').get(user=user)
    print(f'\n=== プロファイル ===')
    print(f'部署ID: {profile.department_id}')
    print(f'部署名: {profile.department.name if profile.department else "なし"}')
    print(f'役職(position): "{profile.position}"')
    print(f'役職バイト: {[hex(ord(c)) for c in (profile.position or "")]}')
except UserProfile.DoesNotExist:
    print('プロファイルが存在しません！')
    profile = None

if profile and profile.department_id and profile.position:
    print(f'\n=== 部署+役職権限検索 ===')
    print(f'検索条件: department_id={profile.department_id}, position_name="{profile.position.strip()}"')

    # 完全一致
    combined_perms = DepartmentPositionPermission.objects.filter(
        department_id=profile.department_id,
        position_name=profile.position.strip(),
    )
    print(f'完全一致結果: {combined_perms.count()}件')
    for p in combined_perms:
        print(f'  {p.resource}: view={p.can_view}, edit={p.can_edit}')

    # 部署のみで検索
    dept_perms = DepartmentPositionPermission.objects.filter(department_id=profile.department_id)
    print(f'\n部署のみ検索結果: {dept_perms.count()}件')
    position_names = set()
    for p in dept_perms:
        position_names.add(p.position_name)
    print(f'登録されている役職名: {list(position_names)}')

# ユーザー個別権限
print(f'\n=== ユーザー個別権限 ===')
user_perms = UserPermission.objects.filter(user=user)
print(f'件数: {user_perms.count()}')
for p in user_perms:
    print(f'  {p.resource}: view={p.can_view}, edit={p.can_edit}')
