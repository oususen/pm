# PG版PM 更新(build up)手順書

- 作成日: 2026-10-23(切替の日)
- 対象: 新PC(10.0.1.139)で動くPG版PM。利用者の入口は `https://10.0.1.139:8501`
- 位置づけ: 切替後の、コード更新・再ビルド・DB変更・戻し方の標準手順。切替そのもの(DBの作成)の手順は `PostgreSQL切替チェックリスト_20261023.md`
- コマンドは、**WSL(Ubuntu、ユーザー daiso)内**で実行する(Windowsのコマンドプロンプトでは動かない)。入るには: `wsl -d Ubuntu -u daiso`

## 0. 構成(これだけ覚える)

| 部品 | コンテナ名 | 場所・役割 |
|---|---|---|
| DB | `pm-pg-q-test` | PostgreSQL 16。**本番DB = `pm_pg_prod_20261023`**(今後ずっと使う)。データは Docker ボリューム `pm-pg-q-test-data` |
| バックエンド | `pm_backend_pg_pc2` | Django + gunicorn。ポート18081 |
| 画面側 | `pm_frontend_pg_pc2` | nginx + Vue。**ポート8501**(利用者の入口)。APK・証明書の配布も担当 |
| スケジューラ | `pm_scheduler_pg_pc2` | 定時ジョブ(発注メール・在庫再計算など)。`--profile scheduler` のときだけ起動 |
| MySQL版(旧) | `mysql` / `pm_backend_prod` / `pm_frontend_prod`(18501) | 戻し先の予備。**触らない** |

- コード: `C:\PST\pm_pg`(WSLでは `/mnt/c/PST/pm_pg`)。構成ファイル: `docker-compose.pc2-pg.yml`
- 設定ファイル: `/mnt/c/PST/pm_pg/.env.pg_rehearsal`(Gitに入れない。DB名・DBパスワード・SECRET_KEY が入っている。**中身を画面に出さない・チャットに貼らない**)
- 全コマンドの共通部分: `cd /mnt/c/PST/pm_pg` と、`-f docker-compose.pc2-pg.yml --env-file .env.pg_rehearsal`

```
cd /mnt/c/PST/pm_pg
DC="docker compose -f docker-compose.pc2-pg.yml --env-file .env.pg_rehearsal"
```

## 1. してはいけないこと

| NG | 理由 |
|---|---|
| `--env-file .env.pg_rehearsal` を付けずに `docker compose up` | DB名が既定値 `pm_pg_q_test`(試験用DB)になり、**別のDBにつながる** |
| `docker compose down -v` / `docker volume rm pm-pg-q-test-data` | **DBのデータが消える**(`-v` はボリューム削除) |
| `python manage.py migrate` を、承認・バックアップなしで実行 | DBが変わる。戻せない(§4) |
| `run_cutover_pc2.sh` を本番DB名で実行 | 切替用。既存のDB名は拒否される。新DBを作るもの |
| MySQL版(`mysql`・`pm_backend_prod`・`pm_frontend_prod`)の停止・削除 | 戻し先 |
| スケジューラのジョブ時刻(後述)に、スケジューラを作り直す | 実行中のジョブが途中で止まる |

## 2. 通常の更新(コードを変えた場合)

### 2-1. 前提の確認

1. 何を変えたか: `git log --oneline -5`、`git diff HEAD~1 --stat`。**DBの変更(マイグレーション)を含むか**を確認(`pm_backend/apps/*/migrations/` に新しいファイルがあれば §4 へ)
2. 時間帯: **業務の少ない時間**。スケジューラのジョブ時刻は避ける(下表)
3. 直前のバックアップがあること(§6)。DBに影響する変更では、更新の直前に取る

| スケジューラのジョブ | 時刻(毎日。設定はDBの `ScheduleConfig`) | 止まると困る度合い |
|---|---|---|
| 発注メールの自動送信 | 07:00 | メールが出ない |
| クボタ堺の納期調整の同期 | 07:45 | 小 |
| 在庫の再計算 | 08:01(PGで約10〜20分) | **大**(途中で止まると、再実行が必要) |
| 手直しアラート | 09:00 | 小 |
| 受注展開 | 18:08 | 中 |
| 納品リストの自動送信 | 19:00 | メールが出ない |
| 計画から実績へのコピー | 19:50 | 小 |

### 2-2. コードを取り込む

- 開発PCで直したものを取り込む場合: 開発PCで `git push` → このPCで `git pull`
- このPCで直接コミットした場合: pull は不要
- `git status` で、意図しない未コミットの変更がないことを確認

### 2-3. 変更した部分だけ作り直す

| 変えたもの | コマンド |
|---|---|
| **バックエンド**(`pm_backend/`) | `$DC --profile scheduler up -d --build pm-backend pm-scheduler` のあと `docker restart pm_frontend_pg_pc2` |
| **画面**(`pm-ui/`)、APK・証明書(`pm-ui/public/downloads/`) | `$DC up -d --build pm-frontend` |
| 構成ファイルだけ(ポート・再起動設定など) | `$DC --profile scheduler up -d`(変更のあるものだけ作り直される) |

- バックエンドは、**画面側のnginxがバックエンドのIPを覚えている**ため、作り直したら、必ず `docker restart pm_frontend_pg_pc2` を実行する(しないと、画面が応答しなくなる。これまでに何度かあった)
- スケジューラは、バックエンドと同じコードを使う。**バックエンドを変えたら、スケジューラも作り直す**(上の1行目に両方入っている)
- `migrate` は、**どのコマンドにも含まれていない**(含めない)。DBを変えるのは §4 だけ

### 2-4. 戻せるようにしておく(推奨)

作り直す前に、いまのイメージに別名を付けておくと、すぐ戻せる。

```
docker tag pm_pg-pm-backend:latest pm_pg-pm-backend:prev
docker tag pm_pg-pm-frontend:latest pm_pg-pm-frontend:prev
```

### 2-5. 更新後の確認

```
docker ps --format '{{.Names}}\t{{.Ports}}\t{{.Status}}' | grep -E "pg_pc2|pg-q-test"   # 4つが Up
docker exec pm_backend_pg_pc2 python -c "import os;print(os.environ['DB_NAME'])"          # pm_pg_prod_20261023
docker exec pm_backend_pg_pc2 python manage.py showmigrations 2>/dev/null | grep -c "\[ \]"   # 0(未適用なし)
docker logs --tail 30 pm_scheduler_pg_pc2                                                  # エラーなし
curl -sk -o /dev/null -w "%{http_code}\n" https://localhost:8501/                          # 200
```

- ブラウザで、`https://10.0.1.139:8501` にログインし、主要画面(受注・生産・在庫)が表示されることを確認する
- **試験で入力したデータは、必ず削除する**(このDBは本番)。削除は、画面の標準の削除を使う(§7の例)
- 記録: 日時、変更内容、コミット、確認結果を、実施記録に残す

### 2-6. 戻す(更新が失敗した場合)

コード・画面だけの変更なら、DBは変わっていない。

```
docker tag pm_pg-pm-backend:prev pm_pg-pm-backend:latest
docker tag pm_pg-pm-frontend:prev pm_pg-pm-frontend:latest
$DC --profile scheduler up -d --no-build pm-backend pm-frontend pm-scheduler
docker restart pm_frontend_pg_pc2
```

その後、ソース側は `git revert <コミット>` で戻す(Gitの履歴を残す)。

## 3. 再起動したとき

- PC・WSLを再起動したら、4つのコンテナは**自動で戻る**(`restart: unless-stopped`)。WSLの起動は、Windowsのタスク `PM-WSL-Start` が保つ
- 戻らない場合: `docker ps -a` で状態を確認し、PGから順に `docker start pm-pg-q-test`、`pm_backend_pg_pc2`、`pm_frontend_pg_pc2`、`pm_scheduler_pg_pc2`
- 起動順は、PG→バックエンド→画面側→スケジューラ。スケジューラは、PGが起動する前だと失敗して、自動で再試行する

## 4. DBを変える更新(マイグレーションを含む場合)

**BOSSの承認が必要**(CLAUDE.md: `migrate` はBOSSの指示で実行する)。

1. 承認を得る(何のマイグレーションか、どの表が変わるか、時間)
2. **バックアップを取る**(§6の `pg_dump`。取れたことと、サイズを確認)
3. 業務の少ない時間に、スケジューラを止める(`docker stop pm_scheduler_pg_pc2`)
4. コードを更新(§2-3、バックエンドを作り直す)
5. 計画を確認: `docker exec pm_backend_pg_pc2 python manage.py migrate --plan`(予定の操作を読む。想定外があれば中止)
6. 実行: `docker exec pm_backend_pg_pc2 python manage.py migrate`
7. 確認: `showmigrations` で未適用0。主要画面を確認
8. スケジューラを起動(`docker start pm_scheduler_pg_pc2`)
9. **戻し方**: マイグレーションは、逆向きに戻せない場合がある。失敗したら、**バックアップから復元**する(§6)。復元の間は、入力を止める
10. MySQL版(旧)には、同じマイグレーションを当てない(戻し先は、切替時点の状態で止める)

## 5. APK・証明書の更新

- **場所**: `pm-ui/public/downloads/app-debug.apk`、`pm-ui/public/downloads/pm-pc2.crt`。**画面側のイメージに焼き込まれる**ため、変えたら `$DC up -d --build pm-frontend`
- 旧本番の案内ページにも、同じファイルを置く(`notice/手順書.md`)
- **証明書の有効期限: 2027-10-22 05:49(JST)ごろ**(新PCのHTTPS証明書 `CN=PM PC2`、自己署名)。期限が切れる前に、更新が必要
  - 更新すると、**APKに組み込んだ証明書(`android/app/src/main/res/raw/pm_pc2.crt`)も古くなり、APKが新PCにつながらなくなる**。証明書の更新と、APKの作り直し・再配布は、セットで行う
  - 利用者のパソコンにインストールした証明書も、入れ直しが必要

### APKの作り直し(今回の方法)

1. Web側のビルドとCapacitorの同期(Dockerで): `docker run --rm -v <コピー先>:/app -w /app -e CAPACITOR_SERVER_URL=https://10.0.1.139:8501 node:20-alpine sh -c "npm ci && npm run build && npx cap sync android"`(コピー先は、`pm-ui` を node_modules なしでコピーした作業フォルダ)
2. Gradleでビルド(Windows側): `JAVA_HOME` を **Java 21**(Gradle 8.11 は Java 25 に非対応。Capacitor 8 は Java 21 が必要)、`ANDROID_HOME` を Android SDK にして、`android\gradlew.bat assembleDebug`
3. リポジトリには、起動画面(`drawable/splash`)が入っていない。作業コピーに単色の `splash.xml` を足してビルドした(開発PCのビルドとは、起動画面が違う)
4. できたAPK(`android\app\build\outputs\apk\debug\app-debug.apk`)を `pm-ui/public/downloads/` に置く
5. **新旧で署名が違うと、上書きインストールできない**(利用者は、旧アプリをアンインストールしてから入れる)

## 6. バックアップと復元

- **バックアップ(設定予定)**: 毎日07:45、Windowsのタスクスケジューラ → WSLのスクリプト → `pg_dump -Fc`、保存先 `D:\database_backup_pg\`、14日分(BOSS決定待ちの項目あり)
- **注意(2026-10-23 確認)**: WSLから D: ドライブが**見えていない**(`/mnt/d` が無い。D: は外付けHDD `HD-NRLD-A`、3.7TB)。D: に書くには、次のどちらかが必要(未設定):
  1. WSLで D: をマウントする: `sudo mount -t drvfs D: /mnt/d`(再起動のたびに必要。常用するなら `/etc/fstab` に `D: /mnt/d drvfs defaults 0 0` を追加)
  2. `pg_dump` は C: 側(`/mnt/c/PST/backup/`)に保存し、Windowsのタスクで D: へコピー(`robocopy`)する(**こちらを推奨**。D: が外れていても、C: にダンプが残る)
  - D: が接続されていないときの失敗に気付けるよう、タスクの結果(最終実行日時・終了コード)を、定期的に確認する
- **手動で取る**(更新の直前):
  ```
  docker exec pm-pg-q-test pg_dump -U pm_pg_admin -Fc pm_pg_prod_20261023 > /mnt/d/database_backup_pg/pm_pg_manual_$(date +%Y%m%d_%H%M%S).dump
  ls -la /mnt/d/database_backup_pg/ | tail -3
  ```
- **復元**(別名のDBに戻して、中身を確認してから使う): `docker exec -i pm-pg-q-test createdb -U pm_pg_admin pm_pg_restore_test` のあと `docker exec -i pm-pg-q-test pg_restore -U pm_pg_admin -d pm_pg_restore_test < <ダンプ>`。本番DBへの上書き復元は、BOSSの承認と、入力の停止が必要

## 7. 日常の確認コマンド

```
docker ps --format '{{.Names}}\t{{.Status}}' | grep -E "pg_pc2|pg-q-test"
docker logs --tail 50 pm_backend_pg_pc2
docker logs --since 1h pm_scheduler_pg_pc2 | grep -a -i -E "error|exception|失敗" | tail
docker exec pm-pg-q-test psql -U pm_pg_admin -d pm_pg_prod_20261023 -c "select count(*) from line_backlog"
```

- 画面で試験データを入れたら、**画面の削除機能で消し**、DBで確認する(例: ブレーキ実績は「実績変更」画面の削除。実績が元に戻る)
- 試験・検証が必要な場合は、**本番DBではなく、外部通信を遮断した試験環境**(`pm-wt-net`、DB `pm_pg_wt1`)で行う。DBは、ダンプから作り直せる(`~/pgq/` のスクリプト)

## 8. よくある問題

| 症状 | 原因・対処 |
|---|---|
| 画面が出ない・APIが応答しない | バックエンドを作り直したあと、画面側を再起動していない → `docker restart pm_frontend_pg_pc2` |
| 「開発環境」のバナー・黄色い背景 | 画面側のイメージが古い(10.0.1.232 を本番と判定していた古い版) → `$DC up -d --build pm-frontend` |
| ログインできない(invalid credentials) | ブラウザの自動入力の違い、または、別ポートの古いログイン情報(クッキー)の衝突。パスワードを手入力、別のブラウザ・プライベートウィンドウで試す |
| PCを再起動したらつながらない | WSLが起動していない → Windowsのタスク `PM-WSL-Start` を確認。`wsl -d Ubuntu` を一度開く |
| 在庫再計算(08:01)が遅い | PGの統計情報が古い → `docker exec pm-pg-q-test psql -U pm_pg_admin -d pm_pg_prod_20261023 -c "ANALYZE;"`(数秒) |
| ディスクが増える | 古いイメージ・試験用DB。`docker image prune`(使用中は消えない)、試験用DB(`pm_pg_q_test`、`rh1`〜`rh5`、`ui`、`wt1`)は、安定後にBOSS承認で `DROP DATABASE` |

## 9. 関連文書

- `PostgreSQL切替チェックリスト_20261023.md`(切替当夜の記録)
- `PG版書込系試験計画.md`(試験の記録、見つかった差と修正)
- `notice/手順書.md`(旧本番の案内ページ)
- `Androidアプリ配布仕様.md`(pm_pg)
