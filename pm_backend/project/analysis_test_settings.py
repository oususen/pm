"""分析履歴テスト専用。実PM DBのマイグレーション・test_pm_dbには触れない。

既存マイグレーションは外部の未管理テーブルに依存するため、ここではモデルから
メモリ上のSQLiteテストDBを作る。MySQL固有DDLの検証の代わりにはしない。
ai_readerは既存開発DBの読み取り専用接続のまま使用する。
"""
from .settings import *  # noqa: F403

DATABASES = {**DATABASES, 'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}}  # noqa: F405
MIGRATION_MODULES = {app.rsplit('.', 1)[-1]: None for app in INSTALLED_APPS}  # noqa: F405
