"""
kaizen_db.sqlからデータをインポートするコマンド
auth_userとUserProfileにデータを作成
"""
import re
from django.core.management.base import BaseCommand
from django.db import transaction
from django.contrib.auth.models import User
from accounts.models import Department, UserProfile


class Command(BaseCommand):
    help = 'kaizen_db.sqlから部署とユーザーデータをインポート'

    def add_arguments(self, parser):
        parser.add_argument(
            'sql_file',
            type=str,
            help='kaizen_db.sqlファイルのパス'
        )

    def handle(self, *args, **options):
        sql_file = options['sql_file']

        self.stdout.write(self.style.SUCCESS(f'Reading {sql_file}...'))

        with open(sql_file, 'r', encoding='utf-8') as f:
            sql_content = f.read()

        # 部署データの抽出
        dept_pattern = r"INSERT INTO `proposals_department`.*?VALUES\s+(.*?);"
        dept_match = re.search(dept_pattern, sql_content, re.DOTALL)

        if not dept_match:
            self.stdout.write(self.style.ERROR('部署データが見つかりません'))
            return

        dept_values = dept_match.group(1)
        dept_rows = re.findall(r'\((\d+),\s*\'([^\']+)\',\s*\'([^\']+)\',\s*(\d+|NULL),\s*(\d+)\)', dept_values)

        # 従業員データの抽出
        emp_pattern = r"INSERT INTO `proposals_employee`.*?VALUES\s+(.*?);"
        emp_match = re.search(emp_pattern, sql_content, re.DOTALL)

        if not emp_match:
            self.stdout.write(self.style.ERROR('従業員データが見つかりません'))
            return

        emp_values = emp_match.group(1)

        with transaction.atomic():
            # 既存データをクリア（UserProfileのみ。auth_userは保持）
            self.stdout.write('既存プロファイルデータをクリアしています...')
            UserProfile.objects.all().delete()
            Department.objects.all().delete()

            # 部署データのインポート
            self.stdout.write('部署データをインポートしています...')
            dept_map = {}

            for row in dept_rows:
                dept_id, name, level, parent_id, display_id = row
                parent_id = int(parent_id) if parent_id != 'NULL' else None

                dept = Department(
                    id=int(dept_id),
                    name=name,
                    level=level,
                    parent_id=parent_id,
                    display_id=int(display_id)
                )
                dept_map[int(dept_id)] = dept

            # 一括保存
            for dept in dept_map.values():
                dept.save()

            self.stdout.write(self.style.SUCCESS(f'部署データ {len(dept_map)}件をインポートしました'))

            # 従業員データのインポート
            self.stdout.write('ユーザーデータをインポートしています...')

            # 従業員データの解析
            emp_rows = re.findall(
                r'\((\d+),\s*\'([^\']+)\',\s*\'([^\']*)\',\s*\'([^\']*)\',\s*\'([^\']*)\',\s*\'([^\']+)\',\s*(\d+),\s*(?:\'([^\']*?)\'|NULL),\s*(\d+),\s*(\d+|NULL),\s*\'([^\']*)\',\s*\'([^\']*)\',\s*\'([^\']*)\',\s*\'([^\']+)\'\)',
                emp_values
            )

            user_count = 0
            for row in emp_rows:
                (emp_id, code, name, email, position, role, is_active,
                 joined_on, dept_id, user_id, division, group, team, employment_type) = row

                try:
                    # auth_userを作成または取得
                    username = code  # 社員コードをユーザー名として使用

                    # 既存ユーザーをチェック
                    user, created = User.objects.get_or_create(
                        username=username,
                        defaults={
                            'email': email if email else '',
                            'first_name': name[:30] if name else '',  # first_nameは最大30文字
                            'is_active': bool(int(is_active)),
                        }
                    )

                    if not created:
                        # 既存ユーザーの場合、情報を更新
                        user.email = email if email else ''
                        user.first_name = name[:30] if name else ''
                        user.is_active = bool(int(is_active))
                        user.save()

                    # UserProfileを作成
                    UserProfile.objects.create(
                        user=user,
                        employee_code=code,
                        position=position,
                        role=role,
                        employment_type=employment_type,
                        department_id=int(dept_id),
                        division=division,
                        group=group,
                        team=team,
                        joined_on=joined_on if joined_on else None,
                    )

                    user_count += 1

                    if created:
                        self.stdout.write(self.style.SUCCESS(f'[新規] ユーザー作成: {username} ({name})'))
                    else:
                        self.stdout.write(f'[更新] ユーザー更新: {username} ({name})')

                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'従業員 {code} のインポート中にエラー: {e}'))
                    continue

            self.stdout.write(self.style.SUCCESS(f'\nユーザーデータ {user_count}件をインポートしました'))
            self.stdout.write(self.style.SUCCESS('データのインポートが完了しました'))
