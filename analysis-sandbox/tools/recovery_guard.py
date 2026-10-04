"""復旧コマンド用の読み取り確認。launcherの標準ロックを保持し、Dockerを変更しない。"""
import errno
import fcntl
import json
import socket
import subprocess
import sys


def main():
    # 標準配置の開発launcherだけが対象。別ロック・別ポートの構成には使わない。
    with open('/run/pm-analysis-launcher.lock', 'a') as handle:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with socket.socket() as sock:
            sock.settimeout(10)
            if sock.connect_ex(('127.0.0.1', 8091)) != errno.ECONNREFUSED:
                raise RuntimeError('launcher_stopped_unconfirmed')
        result = subprocess.run(['docker', 'ps', '-aq', '--filter', 'label=pm.analysis.job=1'],
                                capture_output=True, text=True, timeout=10, check=True)
        if result.stdout.strip():
            raise RuntimeError('containers_present')
        print(json.dumps({'launcher_stopped': True, 'containers_absent': True}), flush=True)
        sys.stdin.read(1)  # 呼出し側の確認・条件付き更新が終わるまでロックを離さない。


if __name__ == '__main__':
    main()
