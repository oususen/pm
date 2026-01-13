from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'Create UserProfile table manually'

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            # UserProfileテーブルを作成
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS `accounts_userprofile` (
                  `user_id` integer NOT NULL PRIMARY KEY,
                  `employee_code` varchar(32) NULL UNIQUE,
                  `position` varchar(100) NOT NULL,
                  `role` varchar(20) NOT NULL,
                  `employment_type` varchar(20) NOT NULL,
                  `division` varchar(100) NOT NULL,
                  `group` varchar(100) NOT NULL,
                  `team` varchar(100) NOT NULL,
                  `joined_on` date NULL,
                  `created_at` datetime(6) NOT NULL,
                  `updated_at` datetime(6) NOT NULL,
                  `department_id` bigint NULL
                )
            """)
            self.stdout.write(self.style.SUCCESS('UserProfile table created'))

            # 外部キー制約を追加
            try:
                cursor.execute("""
                    ALTER TABLE `accounts_userprofile`
                    ADD CONSTRAINT `accounts_userprofile_user_id_92240672_fk_auth_user_id`
                    FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`)
                """)
                self.stdout.write('Added FK to auth_user')
            except Exception as e:
                self.stdout.write(f'FK to auth_user already exists or error: {e}')

            try:
                cursor.execute("""
                    ALTER TABLE `accounts_userprofile`
                    ADD CONSTRAINT `accounts_userprofile_department_id_76402ccc_fk_accounts_`
                    FOREIGN KEY (`department_id`) REFERENCES `accounts_department` (`id`)
                """)
                self.stdout.write('Added FK to department')
            except Exception as e:
                self.stdout.write(f'FK to department already exists or error: {e}')

        self.stdout.write(self.style.SUCCESS('Table setup completed'))
