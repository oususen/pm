# Docker VHDX 圧縮手順（C:ドライブ空き容量対策）

## 背景

Docker Desktop（WSL2バックエンド）は、イメージの再ビルドを繰り返すとビルドキャッシュが仮想ディスク（vhdx）内に蓄積し続ける。vhdxは中身を削除しても**ファイル自体は自動で縮小しない**ため、C:ドライブの空き容量がじわじわ減っていく。

対策は2段階：

1. **ビルドキャッシュ削除**（ダウンタイムなし・いつでも実行可）
2. **VHDX圧縮**（Docker Desktop停止が必要・要ダウンタイム）

この2つを両方行わないと、C:ドライブの空き容量には反映されない。

## 対象コンテナ（このマシンで共有稼働中）

VHDX圧縮はDocker Desktop / WSL2を丸ごと停止するため、以下**全プロジェクト**が数分〜20分停止する。

| プロジェクト | ディレクトリ |
|---|---|
| pm | `C:\PST\pm` |
| syomohin | `C:\PST\syomohin` |
| kaizen_pp | `C:\PST\kaizen_pp` |
| ts_pm_all_v2（共通MySQL含む） | `C:\PST\ts_pm_all_v2` |

**業務時間中の実行は避け、休憩時間や夜間などダウンタイムを許容できるタイミングで行うこと。**

## 手順

### 1. ビルドキャッシュ削除（安全・即実行可）

```powershell
docker system df          # 現状確認（Build Cache の Reclaimable 列を見る）
docker builder prune -f   # 不要な中間キャッシュのみ削除。稼働中コンテナ・イメージには影響なし
docker system df          # 削減後の確認
```

### 2. VHDX圧縮（要管理者権限・要ダウンタイム）

`scripts/compact_docker_vhdx.ps1` を使用する。

```powershell
# 管理者権限のPowerShellで実行（右クリック →「管理者として実行」）
cd C:\PST\pm

# （任意）プレビューのみ。停止・削除は行わない
.\scripts\compact_docker_vhdx.ps1 -WhatIfMode

# 本実行
.\scripts\compact_docker_vhdx.ps1
```

スクリプトが自動で行う内容：

1. Docker Desktop を強制停止
2. `wsl --shutdown` でWSL2をシャットダウン
3. `diskpart` で vhdx を圧縮（数分〜20分）
4. 圧縮前後のvhdxサイズ・C:空き容量を表示

### 3. 復旧確認

1. Docker Desktop を手動で起動
2. 全コンテナが自動復旧しているか確認

```powershell
docker ps
```

対象コンテナは全て `restart: always` または `unless-stopped` 設定のため、通常は自動起動する。もし起動していないコンテナがあれば、該当プロジェクトのディレクトリで個別に起動する。

```powershell
cd C:\PST\pm; docker-compose up -d
cd C:\PST\syomohin; docker-compose up -d
cd C:\PST\kaizen_pp; docker-compose up -d
cd C:\PST\ts_pm_all_v2; docker-compose up -d
```

## 実績（2026-08-25実施）

| 項目 | 圧縮前 | 圧縮後 |
|---|---|---|
| VHDXサイズ | 62.68 GB | 53.25 GB |
| C:空き容量 | 13.85 GB | 29.65 GB |

## トラブルシューティング：スクリプト実行時の構文エラー

管理者権限で実行した際に以下のようなエラーが出た場合、`compact_docker_vhdx.ps1` の**文字コード**が原因。

```
発生場所 ...compact_docker_vhdx.ps1:85 文字:19
+ 式またはステートメントのトークン '[WhatIf]' を使用できません。
ステートメント ブロックまたは型定義に終わりの '}' が存在しません。
```

**原因:** `.ps1`ファイルがUTF-8（BOMなし）で保存されている場合、Windows PowerShell 5.1はBOMがないとシステム既定のコードページ（日本語環境ではShift-JIS系）で読み込むため、日本語コメント部分が文字化けし構文エラーになる。

**対処:** ファイル先頭にUTF-8 BOM（`EF BB BF`）を付与する。

```bash
# Git Bash等で実行
printf '\xEF\xBB\xBF' | cat - scripts/compact_docker_vhdx.ps1 > scripts/_tmp.ps1
mv scripts/_tmp.ps1 scripts/compact_docker_vhdx.ps1
```

以降、日本語コメントを含むps1ファイルを新規作成する際はBOM付きUTF-8で保存すること。
