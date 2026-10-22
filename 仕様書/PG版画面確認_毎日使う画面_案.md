# PG版 画面確認 — 「毎日使う画面」案(約28画面)

- 作成日: 2026-10-22
- 状態: **案(私が作成)。最終的な選択は、BOSS・現場の担当者が、実際の使い方で決める**
- 位置づけ: `PG版画面確認チェックリスト.md`(220画面)のうち、優先して確認する画面。全画面を人が確認するのは現実的でないため、3段階で確認する(下記)
- 選び方の根拠: 旧本番の最新ダンプ(2026-10-22 00:48取得)で、直近14日(2026-10-08以降)にデータが作成・更新されたテーブルの多い領域。**更新が少なくても、毎日見る画面は、BOSS・現場が追加すること**

## 1. 確認の3段階

| 段階 | 対象 | 方法 | 担当 |
|---|---|---|---|
| 1 | この一覧(約28画面) | MySQL版(`https://localhost:8501`)とPG版(`https://localhost:18501`)を、同じ条件で見比べる。表示と、登録・更新(「書込」の画面)を試す | BOSS・現場 |
| 2 | この一覧の各画面が使うAPI | 画面と同じ条件でAPIを両方に呼び、全項目を比べる(クボタ堺納期調整で実施済み) | Claude |
| 3 | 残りの約190画面 | 自動比較済みのAPI(314本中246本一致)で確認。画面ごとの確認は、使うときに気づいたら報告(切替後の見守り) | Claude・現場 |

## 2. 画面一覧(案)

「確認状況」の欄: 2026-10-22時点で分かっていることのみ。空欄は**未確認**。

| # | 領域 | 画面 | パス | チェックリスト# | 書込 | 使用の根拠(直近14日の更新) | 確認状況 |
|---|---|---|---|---|---|---|---|
| 1 | 受注・需要 | 受注一覧 | `/orders` | 74 | | `t_order_line` 20万、`stg_order_daily` 16万 | **API(`/api/orders/?page_size=0`、1,533件)が全項目一致(2026-10-22)**。画面の表示・操作は未確認 |
| 2 | 受注・需要 | ライン需要一覧 | `/production/line-demands` | 7 |  | `t_line_demand` 29万 | API: 440MB級で詳細比較せず(件数・集計はDBで一致) ／ API(`line-demands?product_search=V0531`、13,507件)は**集合として一致、並び順のみ異なる**。全件(`line-demands`、約190MB)は大きすぎて詳細比較せず(件数・集計はDBで一致) |
| 3 | 受注・需要 | 旧OPEN受注洗い出し | `/orders/open-order-audit` | 72 | | 受注 | API: ENUM修正後に200(MySQL版と同サイズ) |
| 4 | 受注・需要 | 受注展開 | `/shipping/order-expansion` | 83 | | 受注 | 要確認(実行系の可能性) |
| 5 | 在庫・進度 | 進度監視 | `/production/progress-monitor` | 11 | | `line_backlog` 4.9万 | **API(`options`と、全7ユニットの`snapshot`: start_date=2026-10-01・horizon=30)が全項目一致(2026-10-22)**。書込系(ピックアップ・再計算・お気に入り)と画面操作は未確認 |
| 6 | 在庫・進度 | 進捗管理 | `/production/progress` | 9 |  | `line_backlog` | API: `production-lines`(27件)は全項目一致(2026-10-22)。画面操作は未確認 |
| 7 | 在庫・進度 | 在庫 / 残量一覧 | `/production/inventory` | 18 | | `line_backlog` | API: `lines`は全項目一致。`line-backlogs`(2026-10-22〜11-20、76,793件、63.7MB)は**集合として一致(件数・全行の内容が同じ)だが、並び順だけ異なる**。画面がこの順序に依存するかは未確認(画面側で並べ替えるか要確認)。再計算・保存などの書込系と画面操作は未確認 |
| 8 | 在庫・進度 | 在庫管理 | `/inventory` | 57 | | `line_backlog` | |
| 9 | 生産計画 | 生産計画入力 | `/production/plan-input` | 12 | ○ | `line_plan` 932 | API: `production-plan-line-settings`・`processes`は全項目一致。`routing-steps`(3ライン)は**集合として一致、並び順のみ異なる**。計画の保存・展開・ガント生成などの書込系と画面操作は未確認 |
| 10 | 生産計画 | 工程ガント | `/production/process-gantt` | 41 |  | `t_line_gantt_plan` 665 | API: `process-display-orders`・`work-patterns`・`lines`は全項目一致。`calendar-days`(8,479件)は**集合として一致、並び順のみ異なる**。画面操作は未確認 |
| 11 | 出荷 | 出荷進度照会 | `/shipping/progress` | 81 | | `t_shipping_progress` 6,321 | API: `shipping-progress`(13,295件)・`shipment-actuals`(122件)は全項目一致。`order-lines`(66,176件)は**集合として一致、並び順のみ異なる**。再計算などの書込系と画面操作は未確認 |
| 12 | 出荷 | 出荷実績照会 | `/shipping/actual` | 78 | | 出荷実績 | |
| 13 | 出荷 | クボタ堺納期調整 | `/shipping/kubota-sakai-due-adjustment` | 87 | | `t_kubota_sakai_due_adjustment` 410 | **API(`grid/?start_date=2026-10-22&horizon_days=30`)が全項目一致(2026-10-22)。画面のスクリーンショットも同じに見える。操作は未確認** |
| 14 | 出荷 | クボタ堺便計画 | `/shipping/kubota-sakai-trip-planning` | 88 |  | `t_kubota_sakai_trip_assignment` 535 | API: `trip-assignments`の`grid`(2026-10-22)・`display-settings`・`pseudo-truck-products`・`load-detail`・`calendars`が**全項目一致(2026-10-22)**。保存・割付などの書込系と画面操作は未確認 |
| 15 | 出荷 | 便確認(出荷担当) | `/shipping/trip-execution` | 89 |  | `t_shipping_trip` 234 | API: `shipping-trips/execution/?departure_date=2026-10-22`が**全項目一致(2026-10-22)**。画面操作は未確認 |
| 16 | レーザー | レーザー実績入力 | `/production/laser-process-input` | 37 | ○ | `t_laser_actual_detail` 2,589 | API: `equipments`・`interruption-reasons`・`laser-actuals`(500件)・`current-processing`・`laser-shift-records`・`material-receipts`・`production-lines`が**全項目一致**。`laser-patterns`(218件)は**集合として一致、並び順(と構成部品の並び)のみ異なる**。実績の登録などの書込系と画面操作は未確認 |
| 17 | 実績入力 | ブレーキライン実績入力 | `/production/brake-line-input` | 44 | ○ | `t_process_work_session` 400 | **PG版で実績入力と設備トラブル記録に成功(BOSS、2026-10-22)。削除は未実施** |
| 18 | 実績入力 | スポット実績入力 | `/production/spot-line-input` | 47 | ○ | `t_process_work_session` | 工程一覧の表示は確認(jsonb修正後)。入力は未確認 |
| 19 | 実績入力 | 工程作業記録 | `/production/mobile-process-input` | 32 | ○ | `t_process_work_session` | |
| 20 | 実績入力 | 仕損品記録 | `/production/scrap-record` | 38 | ○ | 仕損 | |
| 21 | 品質 | 設備点検表 | `/quality/equipment-inspection` | 128 |  | `quality_equipment_inspection_result` 1,542 | API: 点検表テンプレート(22件・実施用14件・詳細3件)、`monthly_overview`(2026-10、6シート)、`unit-line-mappings`が**全項目一致(2026-10-22)**。点検の記録(登録)は未確認 |
| 22 | 品質 | 工程一体チェックシート | `/quality/product-checksheet` | 132 |  | `quality_integrated_cs_sketch_response` 1,493 | API: 工程一体チェックシートのテンプレート(15件・詳細3件)、バッチ一覧(100件)、バッチ詳細・ユニット(3バッチ)、`rework-alert-configs`が**全項目一致(2026-10-22)**。PDF出力・登録は未確認 |
| 23 | 品質 | チェックシート チェック実施 | `/quality/product-checksheet/integrated/operation` | 135 | ○? | 同上 | API: 上記(#22)と同じ画面系統(`operation`)のAPIが全項目一致。チェック実施の登録は未確認 |
| 24 | 残業 | 残業申請 | `/overtime/apply` | 198 |  | `t_overtime_application` 266 | API: `accounts/users`(104件)・`overtime/applications`(0件)が全項目一致。申請の登録は未確認 |
| 25 | 残業 | 残業申請 一覧 | `/overtime/list` | 201 |  | `t_overtime_approval_log` 495 | API: `overtime/applications`・`accounts/groups・teams・units`が全項目一致。PDF出力は未確認 |
| 26 | マスタ | 製品マスタ | `/masters/product` | 141 |  | `m_product` 470 | API: `customers`・`product-groups`・`container-capacities`・`suppliers`・`lines`・`processes`が全項目一致。`products`(2,871件)は**集合として一致、並び順のみ異なる**。登録・更新・取込は未確認 |
| 27 | マスタ | ルーティングマスタ | `/masters/routing` | 155 |  | `m_routing_step` 7,705 | API: `routings`(543件)・`routing-step-materials`(6,460件)・`coproduct-driver-child-products`が全項目一致。`routing-steps`(7,705件)は**集合として一致、並び順のみ異なる**。登録・更新は未確認 |
| 28 | 設定 | 取り込み＋在庫進度計算 | `/settings/inventory-task-settings` | 173 | | 取込・計算の設定 | |

- 「書込」の列は、ルーティングの`permission: edit`の有無から。画面内のボタン(再計算・取込・確定など)でデータを書き換える画面は、他にもある。
- #4・#23は、実行系(展開・確定)の可能性がある。**実行する場合は、必ず、試験用のPG DBで行う。**

## 3. 確認の進め方(各画面)

1. 同じ日付・条件で、MySQL版とPG版を並べて表示する(例: 2026/10/22、期間30日)。
2. 見るポイント: 画面が開く、エラーが出ない、**列・行の並びと、主要な数字が同じ**、並び替え・絞り込み・ページ送りが動く。
3. 「書込」の画面は、試験データを1件登録して、画面に出ることを確認する。**登録した試験データは、後で削除する(削除したことを記録)。**
4. 違いがあれば、画面名・操作・MySQL版とPG版の表示の違いを具体的に報告する(スクリーンショット)。
5. **数字の比較は、PG版を書き換える前に行う**(書き込むと、MySQL版とずれる)。

## 4. 未決定

1. この一覧の、追加・削除(BOSS・現場が、日常で使う画面)
2. 確認の担当者・日程
3. 各画面のAPI比較(段階2)を、どの画面から進めるか(提案: #1、5、7、9、11の順)
