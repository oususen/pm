"""
WSGI config for project project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import os
import sys
from pathlib import Path

from django.core.wsgi import get_wsgi_application

base_dir = Path(__file__).resolve().parent.parent
apps_dir = base_dir / "apps"
if str(apps_dir) not in sys.path:
    sys.path.insert(0, str(apps_dir))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')

application = get_wsgi_application()
