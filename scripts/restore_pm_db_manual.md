# 開発PC 本番DB復元手順

この手順は、`pm_db_backup_*.sql` を開発PCの `pm_db` に復元するための手順です。

## 1. 事前準備

- バックアップファイルを `d:\pm\` に配置する
- バックエンド (`runserver`) を停止する
- PowerShell を開く

## 2. 復元コマンド

`d:\pm` で以下を実行:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\restore_pm_db.ps1 pm_db_backup.SQL
```

## 3. 成功判定

実行後に以下が表示されれば復元成功:

- `Restore completed.`
- `Table count: ...`
- `django_migrations count: ...`

## 4. 復元後作業

- バックエンドを再起動
- ログイン確認
- 必要なら主要画面（通知、部署、生産計画）を軽く動作確認

## 5. よくあるエラー

- `Dump file not found`:
  - バックアップファイル名と配置場所 (`d:\pm`) を確認
- `mysql.exe was not found`:
  - MySQLインストール先を確認し、`-MysqlPath` を指定して再実行

例:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\restore_pm_db.ps1 pm_db_backup_xxx.SQL -MysqlPath "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe"
```

## 6. 参考（オプション）

DB名やユーザーを変える場合:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\restore_pm_db.ps1 pm_db_backup_xxx.SQL -DbName pm_db -DbUser root -DbPassword "your_password"
```
