# 開発PC PG版PM セットアップ手順(本番ダンプで、コード変更をすぐ確認する)

- 作成日: 2026-10-23
- 対象: **開発PC**。本番(新PC 10.0.1.139)のPG版PMのダンプを使い、本番と同じデータで開発・確認する
- 方針(BOSS決定): **DBだけDocker。バックエンド・フロント・スケジューラは、Dockerを使わず、開発PCで直接動かす**(コードを変えた結果が、すぐ見えるため)
- この手順のうち、**DBの復元(§3)は新PCで試験済み**(新しい `postgres:16` コンテナに、2.2GBのダンプを約75秒で復元、286表、アプリのAPIも応答)。**バックエンド・フロントを開発PCで直接動かす部分(§4〜§6)は、新PCにPython・Nodeが無く、未試験**(各手順の確認項目で確かめること)
- 別のセッション(開発PC)に渡す前提で、必要なことだけを書く。本番のDB・サーバーには、一切つながない

## 0. 構成

| 部品 | 開発PCでの動かし方 |
|---|---|
| DB(PostgreSQL 16) | **Docker**(コンテナ `pm-pg-dev`、ポート 127.0.0.1:25432)。本番ダンプを復元して使う |
| バックエンド(Django) | **直接**(`python manage.py runserver 8081`)。Dockerなし |
| フロント(Vue、Vite) | **直接**(`npm run dev`、http://localhost:8501)。Dockerなし |
| スケジューラ | **直接**(`python manage.py run_scheduler`)。**Dockerなし。普段は起動しない**(§7) |

- バックエンドの既定の接続先(`pm_backend/project/settings.py`)は、すでに `127.0.0.1:25432`、DB名 `pm_pg_dev`、ユーザー `pm_pg_admin`。**パスワード(`DB_PASSWORD`)だけを環境変数で渡せば、つながる**

## 1. 前提(開発PCに入れておくもの)

| 道具 | 版 | 備考 |
|---|---|---|
| Docker Desktop | 最新 | DB用だけ |
| Python | **3.12**(本番のDockerfileと同じ) | 仮想環境(venv)を使う |
| Node.js | 20(本番ビルドと同じ) | |
| Git | | リポジトリ `pm_pg` |

## 2. ダンプの入手

- 場所: 新PC(10.0.1.139)の `D:\database_backup\pm_pg_backup_日付_時刻.sql`(毎日07:45に自動で作られる予定。手動なら新PCで `scripts\backup\pg_backup.ps1`)。約2.2GB
- 開発PCへのコピー: ネットワーク共有またはUSB。**最新の1ファイル**だけ
- ダンプは普通のSQLファイル。所有者・権限の情報を含まない(`--no-owner --no-privileges`)ため、**どのPGにも復元できる**
- 注意: ダンプには、本番の業務データ・ユーザー情報が入っている。**開発PC以外へ持ち出さない・クラウドに上げない**

## 3. 開発用DBの復元(Docker、約2〜5分)

開発PCのPowerShellで、リポジトリ直下から:

```
$env:PM_PG_DEV_PASSWORD = '<開発用DBのパスワード。任意の文字列。画面・チャット・Gitに出さない>'
powershell -ExecutionPolicy Bypass -File .\scripts\backup\restore_pg_dev.ps1 -DumpFile <ダンプのパス>
```

- やること: `postgres:16` のコンテナ `pm-pg-dev`(ポート127.0.0.1:25432)を作る → DB `pm_pg_dev` を作る → ダンプを流し込む → **開発用DBのメール(SMTP)設定を無効化** → 統計情報(ANALYZE)
- メール設定の無効化: ダンプには、本番のSMTPのユーザー・パスワード(`accounts_user_smtp_configs`)が入っている。開発から取引先へ実際にメールが出るのを防ぐため、**開発用DBでは `is_active=false`、パスワードを空にする**(新PCで確認済み。本番DBは変わらない)。残したい場合だけ `-KeepMail`(**付けないこと**)
- 作り直す(新しいダンプで入れ替える): 同じコマンドに `-Force` を付ける(開発用DBの中身は消える)
- 成功の目印: 最後に「確認: テーブル 286 表、製品マスタ 約2,872 件」(日々のデータで、件数は少し増える)
- 失敗したら: エラー内容が `%TEMP%\pm_pg_restore_err.txt` に出る。よくある原因: ポート25432が使用中(`-Port` で変える。その場合は `DB_PORT` も合わせる)、Dockerが起動していない、ダンプが途中で切れている(末尾に `PostgreSQL database dump complete` が無い)

## 4. バックエンド(Django)

```
cd pm_backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:DB_PASSWORD = $env:PM_PG_DEV_PASSWORD        # §3と同じパスワード
$env:SECRET_KEY = 'dev-only-secret'
$env:DEBUG = 'True'
python manage.py runserver 8081
```

- `pip install` で `mysqlclient` が失敗した場合: Windows用のビルド環境が無いため。**PG版の動作には使わない**ので、`requirements.txt` から `mysqlclient` の行を除いて入れる(ファイルは書き換えず、コマンドで除く: `Get-Content requirements.txt | Where-Object { $_ -notmatch '^mysqlclient' } | Set-Content $env:TEMP\req.txt; pip install -r $env:TEMP\req.txt`)。AI集計用の `mysql.connector` が必要な場合だけ別に入れる(通常業務は不要)
- **`python manage.py migrate` は実行しない**。本番と同じ状態から始める。新しいマイグレーションを作る開発をする場合は、別途BOSSと確認する(本番への反映は `PG版PM 更新手順(build_up).md` §4)
- 確認: `python manage.py showmigrations` で、`[ ]`(未適用)が無い。http://localhost:8081/api/ が応答する

## 5. フロント(Vue、Vite)

```
cd pm-ui
npm ci
npm run dev
```

- http://localhost:8501 を開く。`/api` は、自動で `http://127.0.0.1:8081`(上のバックエンド)へ中継される(`vite.config.js`)
- HTTPS: 環境変数 `VITE_HTTPS_KEY`・`VITE_HTTPS_CERT` を設定しなければ、HTTPで動く(設定する場合は、開発用の鍵・証明書。**本番の秘密鍵を持ち出さない**)
- コードを保存すると、ブラウザが自動で更新される(これが、Dockerを使わない理由)
- ログイン: ユーザーは、本番と同じ(ダンプに入っている)。パスワードも本番と同じ。**ブラウザの自動入力に注意**(別のアドレスの保存済みパスワードが入る)

## 6. 確認(最初に1回)

1. ログインできる
2. 生産メニュー、ブレーキライン実績入力(工程の一覧が出る)、受注一覧が表示される
3. 画面上で入力しても、**本番には影響しない**(開発用DBだけが変わる)ことを理解しておく
4. コードを少し変えて保存し、ブラウザ・APIに、すぐ反映される

## 7. スケジューラ(Dockerなし、普段は動かさない)

- 開発PCでは、**スケジューラは、通常起動しない**。起動すると、在庫の再計算・受注展開などが、開発用DBを書き換える(開発用DBなので壊れても作り直せる)
- 動作確認が必要なときだけ、バックエンドと同じ環境(venv・環境変数)で、別のターミナルから、直接起動する: `python manage.py run_scheduler`(止めるときは Ctrl+C)
- メール(取引先宛ての自動発注・納品リスト)は、§3のメール無効化により、**送信されない**
- 本番の新PCのスケジューラ(`pm_scheduler_pg_pc2`)とは、無関係。**開発PCから、本番のDB・サーバーに接続しない**

## 8. コードの反映(開発 → 本番)

1. 開発PCでコミット・push(CLAUDE.md の規約どおり。コミット・pushはBOSSの指示で)
2. 新PCで取り込み、`PG版PM 更新手順(build_up).md` の §2(通常の更新)で作り直す
3. DBを変える変更(マイグレーション)は、同 §4(BOSSの承認とバックアップが必要)

## 9. 日々の使い方

- 最新の本番データで始めたいとき: §2で最新のダンプを入手 → §3を `-Force` 付きで実行(約2〜5分)
- 開発用DBを止める・再開: `docker stop pm-pg-dev` / `docker start pm-pg-dev`
- 開発用DBを完全に消す: `docker rm -f pm-pg-dev` と `docker volume rm pm-pg-dev-data`(開発用のみ。本番は別)

## 10. 試験済み・未試験(正直な記録)

| 項目 | 状態 |
|---|---|
| ダンプの作成(新PC、本番DB、約5分、2.2GB、末尾の完了行を確認) | 試験済み |
| ダンプの復元(`restore_pg_dev.ps1`、新しいpostgres:16、約75秒) | 試験済み(新PC。開発PCでは未実施) |
| 復元DBの内容(286表・10,350,138行が本番と全表一致、集計・全行ハッシュ一致、シーケンス遅れ0) | 試験済み(本番DBと同じDBサーバー上の別DBに復元した検証) |
| 復元DBで、Djangoが動く(接続、主要APIが200) | 試験済み(新PCのバックエンドコンテナから接続) |
| メール設定の無効化(開発用DBは有効0件、本番DBは変更なし) | 試験済み |
| 開発PCで、Python・venv・`pip install`・`runserver`、`npm ci`・`npm run dev` | **未試験**(新PCにPython・Nodeが無いため) |
| 開発PCのDocker Desktopで、`restore_pg_dev.ps1` | **未試験**(新PCでは、WSLのDockerを代用して試験) |
