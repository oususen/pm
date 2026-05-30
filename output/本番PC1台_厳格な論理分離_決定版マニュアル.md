# 本番PC1台における「厳格な論理分離」決定版マニュアル

## 1. 2つの世界のガチガチな住み分け

| 項目 | 現場用（本番環境） | `pm_dev`（開発・検証環境） |
| --- | --- | --- |
| 物理PC | 本番PC（1台の筐体を共有） | 同左 |
| OSユーザー | 同一OSユーザーで常時運用（Docker停止防止のためログオフ・ユーザー切替をしない） | 同左（同一ユーザー内で論理分離） |
| フロント (Vue) | Docker内（ポート `8501`） | 生環境（ポート `8505` / `--host 0.0.0.0`） |
| バック (Django) | Docker内（ポート `8081`） | 生環境（ポート `8083` / `0.0.0.0` 起動） |
| `ALLOWED_HOSTS` | `['本番PCの固定IP', '現場端末アクセス元']` | `['本番PCの固定IP', 'テスト端末アクセス元']` |
| MySQL | Dockerコンテナ内MySQL（`pm_prod_db` / 本番用データ、Adminerで操作） | Dockerコンテナ内MySQL（`pm_dev_db` / テスト用データ、本番MySQLとは別コンテナ） |
| DBアクセス権限 | 本番専用DBユーザー（`pm_prod_db` のみ権限） | 開発専用DBユーザー（`pm_prod_db` への権限は一切付与しない） |
| Git管理方法 | `settings.py` は共通化してGit管理。差分は `.env` で管理し、`.env` のみGit除外 | 同左 |

補足:
- `ALLOWED_HOSTS=['*']` は禁止。
- 端末IP固定が難しい場合は、固定IPに加えて管理サブネット制限とリバースプロキシ制限を併用する。
- 本番PCで `Docker Desktop` を使う場合、OSユーザー切替やログオフで本番コンテナが停止する可能性があるため、運用中は同一ユーザーで固定する。
- DBの役割分担は「本番=Docker内MySQL（本番コンテナ）」「開発=Docker内MySQL（開発コンテナ）」とし、共用しない。ローカルMySQLを別途インストールするよりDocker内で分離した方が管理が楽。

## 2. スマホ・現場端末テスト時の正しい通信・権限ルート

外部端末から `pm_dev`（実験室）を安全に叩くための、論理分離された通信フロー。

```text
[テスト用スマホ] (固定IPまたは許可サブネット)
       |
       v ① フロントへアクセス（http://本番PCのIP:8505）
[本番PC 生環境: 開発用ディレクトリの Vue.js]
       |
       v ② API通信（VITE_API_BASE_URL=http://本番PCのIP:8083/api/）
[本番PC 生環境: 開発用ディレクトリの Django]
       |
       v ③ 開発専用DBユーザーで開発用MySQLコンテナに接続
[Docker: 開発用MySQLコンテナ (pm_dev_db のみ権限)]
```

防御ポイント:
- 本番DBと開発DBはDocker内の別コンテナとして分離する（ホスト名・ポートが異なる）。
- 開発側には本番DBの接続情報（ホスト・ユーザー・パスワード）を保持させない。
- 本番アプリ接続先は `DB_HOST=mysql`（本番用コンテナ）、開発アプリ接続先は `DB_HOST=mysql-dev`（開発用コンテナ）に固定する。
- これにより本番DBへの誤接続・誤更新リスクを大幅に低減する。

## 2.1 DB構成の矛盾防止ルール（必須）

1. `.env.prod` と `.env.dev` で接続先・ユーザー・パスワードを完全分離し、共用しない。  
2. Adminerは本番操作用途に限定し、接続先ラベルを明示して誤接続を防ぐ。  
3. 開発起動前チェックで `ENV=dev` かつ `DB_HOST=mysql-dev` を強制検証する。  
4. 本番バックアップ（本番MySQLコンテナ）と開発バックアップ（開発MySQLコンテナ）はジョブと保存先を分離する。  

## 3. ラインを止めないための YOLOv8 運用5大鉄則

1. 時間帯制限（学習の禁止）
開発側の重い学習（`train`）は、生産稼働時間帯は実施しない。稼働時間帯は録画動画による推論（`predict`）のみとする。

2. GPUメモリ上限設定
開発側PyTorchのGPU割り当て上限を設定し、本番コンテナのGPU使用を圧迫しない。

3. 同一ユーザー内での環境分離
作業ディレクトリ、`venv`、ログ保存先、環境変数（`.env.prod` / `.env.dev`）を完全分離する。

4. 温度・負荷監視と自動停止
NVML等で温度/負荷を監視し、閾値超過時は本番保護のため開発側YOLOプロセスを自動停止する。

5. バックアップ分離
本番DBバックアップと開発DBバックアップを別ジョブ・別保存先で運用し、相互上書きを防ぐ。

## 4. 追加の必須ガード

1. 本番コンテナ操作コマンドと開発起動コマンドを分離し、エイリアス/スクリプトで誤操作リスクを低減
2. 開発プロセスには本番用 `.env` を読み込ませない（`ENV=dev` を強制）
3. 接続前チェックをスクリプト化（DB名が `pm_prod_db` / `pm_dev_db` のどちらかを必ず検証）
4. 開発側Djangoの `runserver` は検証用途限定。継続公開が必要なら `gunicorn` 等へ切替
5. 運用中のOSユーザー切替・ログオフ禁止（本番Docker停止防止）

## 5. 結論

この設計は「動くかどうか」ではなく、開発中のバグや高負荷が起きた場合でも、本番への実害を最小化するための運用設計である。

表現上は「完全分離」ではなく、単一筐体内での「厳格な論理分離」と定義する。

## 6. マニュアルを具現化する「論理分離」実装手順書

### 6.1 MySQL: 開発用MySQLコンテナと専用ユーザーの作成

`docker-compose.dev.yml`（開発用）に開発専用MySQLコンテナを追加する。

```yaml
services:
  mysql-dev:
    image: mysql:8.0
    container_name: pm-mysql-dev
    environment:
      MYSQL_ROOT_PASSWORD: dev_root_password
      MYSQL_DATABASE: pm_dev_db
      MYSQL_USER: pm_dev_user
      MYSQL_PASSWORD: 開発用パスワード
    ports:
      - "3307:3306"   # 本番MySQL(3306)とポートを分離
    volumes:
      - pm_dev_mysql_data:/var/lib/mysql
    networks:
      - pm_dev_network

  adminer-dev:
    image: adminer
    container_name: pm-adminer-dev
    ports:
      - "8084:8080"   # 本番Adminer(8082)とポートを分離
    networks:
      - pm_dev_network

volumes:
  pm_dev_mysql_data:

networks:
  pm_dev_network:
```

本番MySQLコンテナ（ポート3306）と開発MySQLコンテナ（ポート3307）が別コンテナ・別ボリュームで動作するため、データの混在が起きない。

運用メモ:

- `DROP` 権限は `MYSQL_USER` のデフォルトでは付与されない（必要時のみroot接続で一時付与）。
- 本番用 `docker-compose.yml` と開発用 `docker-compose.dev.yml` は別ファイルで管理する。

### 6.2 Django: `.env` 分離と起動前チェック

#### Django側: 開発用 `.env.dev`（Git除外）例

```ini
ENV=dev
DB_NAME=pm_dev_db
DB_USER=pm_dev_user
DB_PASSWORD=開発用パスワード
DB_HOST=mysql-dev
DB_PORT=3306
ALLOWED_HOSTS=127.0.0.1,本番PC固定IP
```

#### Vue側: 開発用 `.env.dev`（Git除外）例

```ini
VITE_API_BASE_URL=http://本番PC固定IP:8083/api/
```

Vue開発サーバー起動時に `--mode dev` を指定すると `.env.dev` が読み込まれる。
本番用 `.env.production` の `VITE_API_BASE_URL` は本番ポート(`8081`)を指すため、開発フロントから本番APIを誤って叩くことを防げる。

#### `settings.py` ガード例

```python
import os
from django.core.exceptions import ImproperlyConfigured

ENV = os.getenv("ENV", "prod")
if ENV == "dev":
    from dotenv import load_dotenv
    load_dotenv()

DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")

if ENV == "dev":
    if DB_HOST not in ("mysql-dev", "127.0.0.1") or DB_NAME == "pm_prod_db":
        raise ImproperlyConfigured("危険: dev設定で本番向け接続が検出されました。")
else:
    if DB_HOST in ("mysql-dev", "127.0.0.1"):
        raise ImproperlyConfigured("危険: prod設定で開発DB接続が検出されました。")
```

### 6.3 YOLOv8: GPU上限設定と温度watchdog

#### 推論スクリプト側: GPUメモリ上限設定

```python
import torch

if torch.cuda.is_available():
    torch.cuda.set_per_process_memory_fraction(0.4, device=0)
```

#### 別プロセスwatchdog: `gpu_watchdog.py`

推論ループ内に監視を埋め込むと、ループが停止した場合に監視も止まる。
別プロセスとして常駐させ、開発側YOLOプロセスを外部から監視・停止する。

```python
import time
import subprocess
from pynvml import nvmlInit, nvmlDeviceGetHandleByIndex, nvmlDeviceGetTemperature, NVML_TEMPERATURE_GPU

TEMP_LIMIT = 80
CHECK_INTERVAL = 30
DEV_PROCESS_NAME = "yolo_dev"

def main():
    nvmlInit()
    handle = nvmlDeviceGetHandleByIndex(0)
    print(f"GPU watchdog起動: 温度上限={TEMP_LIMIT}C, 監視間隔={CHECK_INTERVAL}秒")

    while True:
        temperature = nvmlDeviceGetTemperature(handle, NVML_TEMPERATURE_GPU)
        if temperature > TEMP_LIMIT:
            print(f"警告: GPU温度 {temperature}C > {TEMP_LIMIT}C。開発プロセスを停止します。")
            subprocess.run(["taskkill", "/F", "/IM", f"{DEV_PROCESS_NAME}.exe"], capture_output=True)
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
```

運用メモ: watchdog自体はタスクスケジューラまたはサービスとして自動起動させる。

### 6.4 開発起動専用エイリアス（補助的な誤操作防止）

PowerShellプロファイルに登録する。
エイリアスだけでは直接コマンド実行を防げないため、あくまで**settings.pyガードとDB分離を補助する位置づけ**とする。

```powershell
function Start-PmDev {
    Set-Location "C:\factory\pm_dev"
    $env:ENV = "dev"
    $env:DJANGO_SETTINGS_MODULE = "project.settings"
    python manage.py runserver 0.0.0.0:8083
}
Set-Alias -Name devrun -Value Start-PmDev

function Start-PmDevFront {
    Set-Location "C:\factory\pm_dev\pm-ui"
    npm run dev -- --mode dev --host 0.0.0.0 --port 8505
}
Set-Alias -Name devfront -Value Start-PmDevFront
```

運用メモ:

- 本番Docker操作コマンド（`docker compose down` 等）は別名コマンドに分離する。
- エイリアスは利便性向上が主目的。安全性の根幹はsettings.pyガードとDB分離が担う。
