# analysis-sandbox(開発専用・検証段階)

AI分析の生成Python・SQLを、ジョブごとの使い捨てコンテナで隔離して実行するための試験実装。
**本番のcompose・Django・設定画面には接続していない。本番での有効化は、別途BOSSの判断が必要。**

| 場所 | 内容 |
|---|---|
| `job/` | ジョブ用イメージ。`job_main.py`(監督プロセス、PID 1)と`runtime.py`(生成コードの実行環境) |
| `launcher/launcher.py` | Dockerを操作する唯一のプロセス。preflight・設定の完全照合・実行・結果の採否判定・後始末 |
| `tools/build.py` | イメージを作成し、イメージIDを`.image-id`へ記録する(launcherはこのIDと一致しないと拒否) |
| `tests/test_isolation.py` | 実Dockerでの隔離・資源制限・段階の期限・後始末・結果採否のテスト(48件) |

## 使い方(Windows開発PC。WSL2のUbuntu-24.04に導入したDocker Engineを使う)
```
wsl.exe -d Ubuntu-24.04 -u root -- python3 /mnt/d/pm/analysis-sandbox/tools/build.py
wsl.exe -d Ubuntu-24.04 -u root -- python3 -m unittest discover -s /mnt/d/pm/analysis-sandbox/tests -v
wsl.exe -d Ubuntu-24.04 -u root -- python3 /mnt/d/pm/analysis-sandbox/launcher/launcher.py   # 127.0.0.1:8091
```
テスト用の「生成コード」は、テストに書いた攻撃を模したスクリプトで、コンテナの中だけで実行する。Windows・Djangoでは実行しない。

## 注意
- DockerソケットはLinuxのroot相当の権限。launcherは開発PC限定で、127.0.0.1でのみ待ち受ける(認証なし)。
- 数値(tmpfs 128MB、プロセス数128、結果5MB、表10,000行、ログ64KB、各段階の期限60秒)は、すべて検証用の暫定値。
