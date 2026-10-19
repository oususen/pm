# PG検証(pm-pg-rehearsal)専用のsettingsオーバーライド。
# D:\pm_pg の複製側だけで使う一時ファイル。本体(D:\pm)には反映しない。
# 使い方: manage.py --settings=project.settings_pg_rehearsal migrate
import os
from pathlib import Path

from dotenv import load_dotenv

_BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(_BASE_DIR / ".env.pg_rehearsal")

from .settings import *  # noqa: F401,F403

DATABASES["default"] = {
    "ENGINE": "django.db.backends.postgresql",
    "NAME": os.environ["PM_PG_DB"],
    "USER": os.environ["PM_PG_USER"],
    "PASSWORD": os.environ["PM_PG_PASSWORD"],
    "HOST": os.environ["PM_PG_HOST"],
    "PORT": os.environ["PM_PG_PORT"],
    "CONN_HEALTH_CHECKS": True,
}
