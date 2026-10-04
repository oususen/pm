#!/bin/bash
# 開発のlauncher(127.0.0.1:8091で待ち受けるプロセス)だけを停止する。
# 別のプロセスを止めないよう、ポートを使うプロセスの実行内容がlauncher.pyであることを確認してから停止する。
pid=$(ss -ltnp 2>/dev/null | grep ':8091 ' | grep -o 'pid=[0-9]*' | head -1 | cut -d= -f2)
if [ -z "$pid" ]; then
    echo "launcherは動いていません。"
    exit 0
fi
if tr '\0' ' ' < "/proc/$pid/cmdline" | grep -q 'launcher/launcher.py'; then
    kill "$pid"
    sleep 1
    echo "launcherを停止しました(PID $pid)。"
else
    echo "8091番ポートを使っているのはlauncherではないため、何も止めていません(PID $pid)。"
    exit 1
fi
