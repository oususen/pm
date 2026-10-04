# analysis-sandbox(開発専用・検証段階)

AI分析の生成Python・SQLを、ジョブごとの使い捨てコンテナで隔離して実行するための試験実装。
**開発のDjangoから接続する。本番のcomposeには組み込まず、本番での有効化は別途BOSSの判断が必要。**

| 場所 | 内容 |
|---|---|
| `job/` | ジョブ用イメージ。`job_main.py`(監督プロセス、PID 1)と`runtime.py`(生成コードの実行環境) |
| `launcher/launcher.py` | Dockerを操作する唯一のプロセス。preflight・設定の完全照合・実行・結果の採否判定・後始末 |
| `tools/build.py` | イメージを作成し、イメージIDを`.image-id`へ記録する(launcherはこのIDと一致しないと拒否) |
| `tests/test_isolation.py` | 実Dockerでの隔離・資源制限・段階の期限・後始末・結果採否のテスト(49件) |

## 使い方(Windows開発PC。WSL2のUbuntu-24.04に導入したDocker Engineを使う)
```
wsl.exe -d Ubuntu-24.04 -u root -- python3 /mnt/d/pm/analysis-sandbox/tools/build.py
wsl.exe -d Ubuntu-24.04 -u root -- python3 -m unittest discover -s /mnt/d/pm/analysis-sandbox/tests -v
wsl.exe -d Ubuntu-24.04 -u root -- python3 /mnt/d/pm/analysis-sandbox/launcher/launcher.py   # 127.0.0.1:8091
```
テスト用の「生成コード」は、テストに書いた攻撃を模したスクリプトで、コンテナの中だけで実行する。Windows・Djangoでは実行しない。

## PM画面から実行する（2-C後半、開発限定）

1. 開発Memuraiと上記launcherを起動する。開発Djangoは`DEBUG=True`かつ既存の`AI_ANALYSIS_LAUNCHER_URL=http://127.0.0.1:8091`が必要。
2. 別のPowerShellで、専用ワーカーを明示起動して端末を維持する：
   ```powershell
   Set-Location D:\pm\pm_backend
   & D:\pm\venv\Scripts\python.exe manage.py analysis_worker
   ```
3. 分析案・データ範囲・コードを承認し、SQL試行が同じハッシュで合格していれば「分析を実行」が使える。実行状態・結果は手動で再取得する。自動実行・自動再送はしない。
4. 中止はジョブIDとランダムな制御トークンでlauncherへ通知し、コンテナを停止・削除する。トークンはRedisの内部情報で、画面には返さない。`cancel_requested`は中止完了ではない。DB接続・コンテナの後始末がpending／failed／unconfirmedなら新しい実行を受け付けない。
5. 結果はRedisだけへ、終了時から分析案キャッシュ有効期限の設定値と同じ期間保持する。コード・結果・明細をDB履歴へ保存せず、社外AIへも送らない。

専用ワーカーの生存確認は既存の10秒／60秒を再利用する。状態不明の枠を自動解放しない。プロセス停止・Redis再起動・削除失敗後の管理者による復旧は、Dockerと履歴の確認が必要で、UIから強制解除する経路は作っていない。稼働中はワーカー／launcherを停止せず、まず画面で中止と後始末を確認する。

ワーカーは同一ホストのOS一時フォルダに1バイトのロックファイルを作り、プロセス終了までロックする。名称は接続先と名前空間のハッシュで、データ・秘密情報は入れない。Redisの停止／再起動で二重ワーカーにならないための保護であり、異常終了した実行の後始末を証明するものではない。起動時にlauncherの隔離・使用中でないことも確認する。

## 未確認の実行枠の復旧（開発限定、管理コマンド）

1. まず中止・実行状態・履歴を確認する。DB接続がpending／failed／unconfirmedなら、このコマンドは解除しない。DB後始末の証拠が足りない場合は調査が必要で、強制的にclosedを書き込んではならない。
2. ワーカーとlauncherを停止する。ジョブ用コンテナが残る場合は、launcherの通常の起動時掃除・中止で削除を確認してから再度停止する。Portainerや他のコンテナは対象にしない。ワーカー生存キーの既存期限（60秒）も待つ。
3. PowerShellで確認だけを実行する（ジョブID必須）：
   ```powershell
   Set-Location D:\pm\pm_backend
   & D:\pm\venv\Scripts\python.exe manage.py analysis_recover --job-id <対象のUUID>
   ```
4. 確認に合格した対象だけ、同じコマンドに`--apply`を付けて解除する。実行時も再確認し、対象ID・状態が変わっていれば解除しない。Redisのactiveキーを手で無条件削除する手順・FLUSHは使わない。
5. launcher・ワーカーを再起動する。結果不明はunknownのまま残り、結果本文は復元しない。古い画面で自動再実行せず、新しい分析案で利用者が明示して進める。

対象は標準のUbuntu-24.04／`127.0.0.1:8091`／`/run/pm-analysis-launcher.lock`。別ホスト・別ポート・独自ロック配置には使わない。コマンドはWindowsのワーカーロックとWSLのlauncherロックを更新完了まで保持し、Dockerの分析ジョブラベル一覧を読むだけ（Dockerの停止・削除は行わない）。必要な確認が一つでも失敗したら解除しない。DB履歴保存にも失敗すれば解除しない。

未確認の終端ジョブはワーカーが10秒ごとに再照合する。ワーカーの処理例外は意図的に停止させ、生存キーを条件付き削除し、実行枠を保持する。復旧で成功と推測しない。

## 再現可能なテスト（追加修正）

出力関数の静的／外枠検査、AIを呼ばない外枠更新、復旧と履歴権限の回帰：
```powershell
Set-Location D:\pm\pm_backend
& D:\pm\venv\Scripts\python.exe -B manage.py test ai.test_analysis_followup --settings=project.analysis_test_settings --noinput
Set-Location D:\pm\pm-ui
node --test scripts/test-analysis-execution-ui.mjs scripts/test-analysis-codegen-ui.mjs
```

外枠の実行時型違反は`child_exit_nonzero`にまとまる。ジョブ用イメージは再作成せず、実コンテナの新外枠テストは`test_codegen_outputs.py`で確認する。SQLだけの試行成功はPythonの出力形式を保証しない。

```powershell
wsl.exe -d Ubuntu-24.04 -u root -- python3 -m unittest discover -s /mnt/d/pm/analysis-sandbox/tests -p test_codegen_outputs.py -v
wsl.exe -d Ubuntu-24.04 -u root -- python3 -m unittest discover -s /mnt/d/pm/analysis-sandbox/tests -p test_recovery_guard.py -v
```

2026-10-04の追加差分はフロント52件、バックエンド184件（176件成功・実launcher用8件skip）、Docker隔離49・中止6・新外枠3件、launcher模擬4・復旧確認模擬4件を確認した。Docker群はグループ別の最終実行で成功（初回一括時の中止3件は旧closed期待値をnot_startedとの区別へ修正し、中止6件を再実行）。実WSLの復旧確認は稼働中launcherのロックを検知して拒否し、既存launcherを停止しなかった。実運用の枠解除・停止済み環境での解除は未検証。実ブラウザ・実AI・独立プロセスの通し、P2-1（操作APIの資源権限）・P3-9（試行の回数／間隔制限）は別途確認・BOSS判断待ち。

```powershell
Set-Location D:\pm\pm_backend
& D:\pm\venv\Scripts\python.exe -B manage.py test ai.test_analysis_jobs ai.test_analysis_execution --noinput
& D:\pm\venv\Scripts\python.exe -B manage.py test ai.test_analysis_run --settings=project.analysis_test_settings --noinput
$env:AI_ANALYSIS_LAUNCHER_URL_FOR_TEST='http://127.0.0.1:8091'
& D:\pm\venv\Scripts\python.exe -B manage.py test ai.test_analysis_execution_flow --settings=project.analysis_test_settings --noinput
```

履歴・通しテスト専用設定は一時SQLiteをモデルから作成する。開発PM DBへのmigrate・既存test_pm_dbの変更はしない。MySQL固有DDL、本番、実AI、ブラウザからの通し操作を確認したことにはならない。通しテストのワーカーは別スレッドであり、独立プロセスの耐障害確認と区別する。

launcherの中止テスト：`wsl.exe -d Ubuntu-24.04 -u root -- python3 -m unittest discover -s /mnt/d/pm/analysis-sandbox/tests -p test_job_cancel.py -v`。実行中・転送中・preflight中の中止、別ジョブ／別トークン、後始末未確認を検証する。

## 注意
- DockerソケットはLinuxのroot相当の権限。launcherは開発PC限定で、127.0.0.1でのみ待ち受ける。ジョブ制御はトークンで照合するが、既存のジョブ受付・healthは全体認証なし（ローカル管理ツールという前提を維持）。
- 数値(tmpfs 128MB、プロセス数128、結果5MB、表10,000行、ログ64KB、各段階の期限60秒)は、すべて検証用の暫定値。
