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

from accounts.models import DepartmentPositionPermission, Department

print('=== 全ての部署+役職権限設定 ===')
all_perms = DepartmentPositionPermission.objects.select_related('department').all()

# 部署ごとにグループ化
dept_positions = {}
for p in all_perms:
    dept_name = p.department.name if p.department else 'なし'
    if dept_name not in dept_positions:
        dept_positions[dept_name] = set()
    dept_positions[dept_name].add(p.position_name)

for dept, positions in sorted(dept_positions.items()):
    print(f'\n{dept}:')
    for pos in sorted(positions):
        print(f'  - {pos}')

print('\n\n=== 全部署一覧 ===')
for d in Department.objects.all():
    print(f'{d.id}: {d.name}')
