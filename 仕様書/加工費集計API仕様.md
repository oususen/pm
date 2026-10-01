# 加工費集計API仕様（/overtime/productivity-stats）

## 概要

勤務 > 加工費集計画面が使う集計専用API。レーザー・ブレーキ・工程実績の3系統を、サーバー側で「作業者 × 日付」単位に集計して返す。
従来は画面が3系統の生データを全件取得してブラウザで集計していたため遅かった（9月分で約25秒）。現在は約4秒。

- **エンドポイント**: `GET /api/productivity-stats/?date_from=YYYY-MM-DD&date_to=YYYY-MM-DD`
- **実装**: `pm_backend/apps/production/views_productivity_stats.py`（`ProductivityStatsView`）
- **認証**: ログイン済みであること（`IsAuthenticated`）
- **件数上限**: なし（3系統とも期間内の全件を対象とする）
- **保存**: なし（リクエストごとに計算。新規テーブルなし）

## レスポンス

```json
{ "rows": [ { "name": "氏名", "date": "YYYY-MM-DD", "qty_total": 0.0, "amount_total": 0.0, "session_seconds": 0 } ] }
```

| 項目 | 意味 |
|---|---|
| `qty_total` | 加工数合計 |
| `amount_total` | 加工費合計（数量 × 品番の単価 `Product.unit_price`、単価未登録は0） |
| `session_seconds` | セッションの実働秒合計（残業の隙間控除前。控除は画面側で行う） |

氏名は空白除去・小文字化したキーで同一人物として集計し、`name` は最初に現れた表記を返す。

## 取得元と計算

| 系統 | テーブル | 期間条件 | 作業秒 |
|---|---|---|---|
| レーザー | `t_laser_actual` + 明細(COMPONENTのみ) | `work_date` | 設備ごとに START/RESUME から次の記録までの秒数。END/PAUSE のみ対象 |
| ブレーキ | `BrakeLineRecord` → `build_brake_sessions()` | `plan_date` | 記録から組み立てたWORKセッションの実働秒（休憩控除後） |
| 工程実績 | `t_process_work_session`（WORK・END/PAUSE） | `plan_date` | ラインカレンダ（勤務パターン＋休憩）で区切った実働秒。連産は子品番へ展開 |

- 集計対象は、数量が0でない END/PAUSE のWORKセッションのみ。
- 重複排除: 日付・氏名・工程コード・品番・終了アクション・数量・開始/終了時刻（秒）が同一の行は、レーザー → ブレーキ → 工程実績の順で先勝ち。
- ブレーキのセッション組み立て（`build_brake_sessions`）は `/brake-line-sessions/` と共通。休憩控除のDB問い合わせは1リクエスト内でキャッシュする（出力は従来と同一）。

## 画面側の処理（`OvertimeProductivityStats.vue`）

- 本APIの結果に、残業申請（出勤時間・隙間控除）を突き合わせて、日別/期間別の表示、順位、色分けを計算する（従来どおり）。
- 加工時間(H) = (`session_seconds` − 残業の隙間分) ÷ 3600。

## 変更履歴

- 2026-10: 集計専用APIを新設。従来の工程実績APIの `limit` 上限（2000件）による欠落（約2000セッションを超える期間）が解消された。
