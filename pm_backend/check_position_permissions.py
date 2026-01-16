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

from accounts.models import PositionPermission, DepartmentPermission, Department

print('=== 役職のみ権限（PositionPermission） ===')
position_perms = PositionPermission.objects.all()
positions = {}
for p in position_perms:
    if p.position_name not in positions:
        positions[p.position_name] = []
    positions[p.position_name].append(f'{p.resource}: view={p.can_view}, edit={p.can_edit}')

for pos, perms in sorted(positions.items()):
    print(f'\n{pos}:')
    for perm in perms:
        print(f'  {perm}')

if not positions:
    print('(なし)')

print('\n\n=== 部署のみ権限（DepartmentPermission） ===')
dept_perms = DepartmentPermission.objects.select_related('department').all()
depts = {}
for p in dept_perms:
    dept_name = p.department.name if p.department else 'なし'
    if dept_name not in depts:
        depts[dept_name] = []
    depts[dept_name].append(f'{p.resource}: view={p.can_view}, edit={p.can_edit}')

for dept, perms in sorted(depts.items()):
    print(f'\n{dept}:')
    for perm in perms:
        print(f'  {perm}')

if not depts:
    print('(なし)')
