"""ジョブ用イメージを作成し、そのイメージIDを .image-id へ記録する(launcherは、このIDと一致しないと実行を拒否する)。

WSLのUbuntu(開発専用)で実行する:  wsl.exe -d Ubuntu-24.04 -u root -- python3 /mnt/d/pm/analysis-sandbox/tools/build.py
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IMAGE = 'pm-analysis-job:dev'


def main():
    subprocess.run(['docker', 'build', '-t', IMAGE, str(ROOT / 'job')], check=True)
    image_id = subprocess.run(
        ['docker', 'image', 'inspect', IMAGE, '--format', '{{.Id}}'], check=True, capture_output=True, text=True,
    ).stdout.strip()
    (ROOT / '.image-id').write_text(image_id + '\n', encoding='ascii')
    print(f'イメージID: {image_id}')


if __name__ == '__main__':
    sys.exit(main())
