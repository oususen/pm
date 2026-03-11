# kikan_input.py 使用手順

生産実績照会のExcel出力2データを基幹システム(SSE0040)に自動入力するスクリプトです。

## 事前準備

```bash
pip install pyautogui pyperclip openpyxl pywin32 keyboard
```

## 使用手順

1. 基幹システムを起動し、SSE0040（生産実績入力）を開く
2. **処理区分フィールドにカーソルを置いた状態**にする
3. 以下のコマンドを実行

```bash
python kikan_input.py production_record2_20260310_20260312.xlsx
```

4. カウントダウン中に基幹システムの画面を前面に出す
5. 自動入力が始まる

## 緊急停止

マウスを**画面の左上角**に移動すると即座に停止します。

---

## ★ Tab数の調整（重要）

スクリプト内の設定値が実際の画面と合わない場合は `kikan_input.py` の以下の箇所を修正してください。

```python
TABS_TO_SEISANBI    = 1   # 処理区分 → 生産日
TABS_TO_HINBAN      = 1   # 生産日   → 品番
TABS_AFTER_HINBAN   = 2   # 品番確定後 → 工程順位  ★要確認
TABS_TO_SEISANSU    = 5   # 工程順位 → 生産数(完成)  ★要確認
TABS_TO_JIKAN_START = 5   # 生産数(完成) → 加工時間1(開始)  ★要確認
TABS_TO_JIKAN_END   = 1   # 加工時間1(開始) → 加工時間1(終了)  ★要確認
```

### Tab数の確認方法

基幹システムで手動操作しながらTabキーを押した回数を数えてください。

---

## 入力フィールド対応表

| Excel出力2の列 | 基幹システムフィールド |
|---|---|
| 生産日（YYYYMMDD） | 生産日（YYYY/MM/DD変換） |
| 基幹品番 | 品番 |
| 工順 | 工程順位 |
| 生産数量 | 生産数(完成) |
| 開始時間（HHMM） | 加工時間1 開始（HH:MM変換） |
| 終了時間（HHMM） | 加工時間1 終了（HH:MM変換） |

※ 生産No・加工者・得意先・仕損数・不良数はスキップ
