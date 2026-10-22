# 本番PC WSL LAN接続不可（8501番）対処記録

記録日: 2026-10-22

## 症状

- 他PCから本番PM画面（`https://10.0.1.232:8501`）に接続できない。
- 同じ本番PCの11435番（LLMゲートウェイ）には届く（404は接続先にトップ画面がないだけで正常）。

## 切り分け結果

| 確認項目 | 結果 |
|---|---|
| 通信記録（pktmon） | 8501番の接続要求は本番PCのWindowsまで到達。WSLへ渡す仮想スイッチ（VFP）で破棄。WSLには届かない |
| ESET | 原因ではない（11435番が同じ経路で通るため） |
| `.wslconfig` | `networkingMode=mirrored`（WSLへの着信をHyper-Vファイアウォールが判定） |
| WSL用Hyper-Vファイアウォール既定の着信 | `DefaultInboundAction : Block`、`Enabled : True` |
| 11435番のルール | WSL専用（VMCreatorId `{40E0AC32-46A5-438A-A0B2-2B479E8F2E90}`）の許可ルールあり → 通る |
| 8501番のルール | `PM-PC2 8501/8081/8082 (LAN)`（VMCreatorId `Any`、Windowsから引き継いだもの）のみ。WSLには効かない → 破棄 |

## 原因

WSL用Hyper-Vファイアウォールの既定の着信が Block であり、8501番などにはWSL専用（VMCreatorId 指定）の許可ルールがなかった。

## 対処

管理者PowerShellで、本番PC（DESKTOP-EQ5E9KP）上で次を実行した。新規ルール追加のみで、既存ルールの変更・WSL/Docker/PMの再起動は行っていない。

```powershell
New-NetFirewallHyperVRule -Name PM-WSL-LAN -DisplayName PM-WSL-LAN `
  -Direction Inbound -Action Allow -Enabled True -Profiles Any `
  -Protocol TCP -LocalPorts 8501,8081,8082,9443,18501 `
  -RemoteAddresses 10.0.0.0/16 `
  -VMCreatorId '{40E0AC32-46A5-438A-A0B2-2B479E8F2E90}'
```

- 結果: Action=Allow、Enabled=True、EnforcementStatus=OK（WSLの3ポートすべてに適用）。
- 他PCからの接続成功をBOSSが確認済み（2026-10-22）。

## 注意点

- ルール追加には管理者権限（昇格したPowerShell）が必要。昇格していないと `Windows System Error 5`（アクセスが拒否されました）になる。
- 確認コマンド: `([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole('Administrator')` が True であること。
- 接続元は既存ルールに合わせ `10.0.0.0/16`。特定IPに絞る場合は `-RemoteAddresses` を変更する。
- WSLで新しいポートを外部公開するときは、Windowsファイアウォールのルールに加え、同様にWSL専用のHyper-Vファイアウォールルールも必要。

## 元に戻す場合

```powershell
Remove-NetFirewallHyperVRule -Name PM-WSL-LAN
```

## 未確認事項

- 本番PCの再起動後にルールが残ること（未確認）。
