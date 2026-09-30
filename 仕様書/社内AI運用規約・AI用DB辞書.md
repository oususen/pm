# 社内AI運用規約・AI用DB辞書

## 1. 目的

社内AIは、PMに蓄積された生産管理データを根拠として、次の業務を支援する。

- 生産・品質・中断・残業・進度などの状況把握と傾向分析
- トラブル発生時の事実整理、原因候補の整理、過去事例の検索支援
- 管理者・幹部会向けの説明資料および報告書の下書き
- 利用者の質問に対する、根拠と対象期間を明示した回答

社内AIは判断を補助する機能であり、製造指示・発注・出荷・在庫調整・人事評価を自動決定または自動実行しない。

## 2. 規約を強制する場所

- 正式な規約本文: 本書
- 規約をコードで強制する入口: `pm_backend/apps/ai/services/chat_service.py`の`AIChatAPIView`（旧 `ProductionAIDemoView`という名称、および互換入口だった `production/views_ai_demo.py` と `production/services/ai_demo_service.py`、旧URL `/api/production-ai-demo/` は削除済み）
- 画面: `pm-ui/src/views/ai/AIChat.vue`（`/ai/chat`）
- 運用設定の管理画面: `pm-ui/src/views/settings/AISettings.vue`（`/settings/ai`、権限 `settings.ai`）

モデルの変更（DeepSeek、Qwenなど）は許可するが、本書のデータアクセス・外部送信・禁止操作の規約を迂回してはならない。2-1 の運用設定で有効化できる範囲も、本書が許可した範囲を超えてはならない。

### 2-2. 権限のサーバー側検証

このプロジェクトは基本的に「権限判定はフロントエンドで行い、バックエンドは`IsAuthenticated`（ログイン済みであること）だけを見る」という設計方針（`accounts/permissions.py`の`HasResourcePermissionOrReadOnly`）を取る。ただし社内AIチャットは、次の2点についてサーバー側でも権限を検証する。

- `ai.chat`: `POST/GET /api/ai/chat/`の入口で、`accounts`の実効権限（`_build_effective_permissions`と同じ判定）に`ai.chat`の閲覧権限がなければ403を返す。
- `overtime.personal_summary`: フロントエンドが送る`allow_personal_overtime`は、サーバー側でも同じ実効権限を確認し、権限がなければ強制的に無効化する。フロントの申告だけを信用しない。

これは、個人別残業（誰がいつどれだけ残業したか）が社内でも特に慎重に扱うべきデータであり、`allow_personal_overtime`のようなクライアント申告のブール値だけを信用すると、ログイン済みの任意の利用者が直接APIを叩いて個人別残業を閲覧できてしまうために例外的に追加した。他のリソースへは展開しない。

## 2-1. 運用設定管理（画面: `/settings/ai`）

社内AIの一部の挙動は、コード変更なしに管理画面から調整できる。ただし調整できる範囲は本書が許可した範囲内に限り、画面(`ai/context/screen_context.py`)が許可していないツールを有効化しても使われない。

| 設定モデル（テーブル） | 内容 | 備考 |
|---|---|---|
| `AIProviderConfig`（`ai_provider_config`） | DeepSeek／Qwenの有効化・既定モデル | APIキー自体は含まない（4.3参照） |
| `AIToolPolicy`（`ai_tool_policy`） | 画面領域(`screen_id`)ごとに、ツール(`tool_code`)を有効化するか、外部AI（DeepSeek）への結果送信を許可するか(`allow_external_transfer`) | 無効化した組み合わせはDeepSeek・Qwenどちらからも呼べない |
| `AIDataPolicy`（`ai_data_policy`） | 集計結果の外部送信可否(`allow_aggregated_external_transfer`)、権限者への個人別集計許可(`allow_authorized_personal_data`)、外部送信する最大集計行数(`max_external_result_rows`) | 常に1行だけ保持する全体方針 |
| `AIKnowledgeSource`（`ai_knowledge_source`） | AIに参照させるリポジトリ内ドキュメントの登録（PMアプリ構造／マニュアル／手順書／安全・運用規約） | 参照させるファイルは登録済みのものに限る |

画面領域(`screen_id`)は `ai_home`（本社横断）、`orders`、`production`、`quality`、`overtime`、`purchase`、`shipping`、`inventory` を持つ。`purchase`／`shipping`／`inventory` は現時点でどのツールも割り当てていない（9章の区分Cに対応）。

## 3. 絶対禁止事項

### 3.1 DB操作

社内AIは、DBに対して次を実行してはならない。

- INSERT、UPDATE、DELETE、UPSERT
- DDL（CREATE、ALTER、DROP、TRUNCATE）
- 更新系SQL、ストアドプロシージャ、管理コマンドの実行
- 生産計画、在庫、受注、発注、出荷、承認、権限の変更

AIが利用するDBアクセスは、規約に登録したDjango ORMの読み取り専用集計関数、または「AI用DB辞書の読み取り専用SQL」に限る。SQLは`pm_ai_reader`接続で実行し、`SELECT`一文・辞書登録済みテーブルと列・最大行数の範囲だけを許可する。モデル名やテーブル名を質問文に含めても、辞書外の列・テーブル、複数文、コメント、ワイルドカード取得は実行してはならない。

### 3.2 業務判断

- 個人の評価、順位付け、査定、懲戒判断をしない。
- 品質判定、出荷可否、発注承認などの最終判断をしない。
- 根拠データが不足する場合、推測で数値や原因を断定しない。

## 4. DeepSeekなど外部APIの利用規約

### 4.1 送信の原則

外部APIへは、回答生成に必要な最小限の情報だけを送信する。送信するデータは、規約に登録された取得関数の出力に限定する。

| データ種別 | 外部送信 | 条件 |
|---|---|---|
| 質問文・直近会話 | 条件付き許可 | 識別子を伏字化して送る |
| 集計済み生産実績 | 許可 | 品番・工程・期間・数量など分析に必要な最小項目 |
| 集計済み仕損・中断 | 許可 | 理由・工程・期間・数量または件数 |
| グループ単位の残業集計 | 許可 | 氏名を含めない |
| 個人別・明細別データ | 条件付き許可 | 個人別残業集計は画面の `overtime.personal_summary` 閲覧権限がある場合だけ、識別子を一時IDへ置換して送信する。氏名指定の個人別集計（`search_employee`で候補確認後に`get_individual_overtime`）としきい値超過者集計（`get_personal_overtime_threshold`）の両方が対象 |
| 本人の残業集計 | 許可 | 利用者本人の分だけを集計する（対象ユーザーはサーバーがログイン者に固定。氏名は結果に含めず、時間・件数だけを送信）。DeepSeek/OpenRouterは `get_my_overtime` を使い、ローカルQwenはサーバー側の固定集計を使う。`overtime.personal_summary` は不要で、`ai.chat` の権限があれば使える。他人の分は調べられない |
| 連絡先、認証情報、署名、添付ファイル | 禁止 | 伏字化しても送信しない |
| 未集計の全件エクスポート | 禁止 | 件数に関係なく送信しない |

### 4.2 伏字化と復元

個人名、ログインID、得意先名、仕入先名など、分析上必要な識別子は以下の方式で扱う。

1. サーバー内で一時ID（例: `作業者A`、`得意先X`、`仕入先A`）に置換する。
2. 対応表はリクエスト処理中のメモリだけに保持し、外部APIへ送信しない。
3. API応答に一時IDが含まれる場合だけ、画面へ返す直前に元の表示名へ復元する。
4. メールアドレス、住所、署名画像、認証情報は復元対象にせず、外部APIへ送信しない。電話番号は、連絡先の列（`phone_number` 等）を個人情報列として制御するが、文字列としての置換は行わない（品番・得意先コードなどの数字の並びを電話番号と誤判定して値が失われたため、2026-10-01に置換を廃止）。

伏字化で必要な分析ができない場合は、対象項目、送信目的、保存有無を規約に追記し、承認後に範囲を拡張する。

会話履歴（`ai_conversation`）には、画面に表示した復元後の回答（権限者の場合は氏名・個人別残業時間を含む）を保存する。外部APIへは送らず、閲覧・削除は会話の作成者本人に限る。対応表（一時ID⇔実名）自体は保存しない。保存期間はAI設定の「会話履歴の保存期間」で管理し（0は無期限）、期限を過ぎた会話は自動削除する。

### 4.3 APIキー

- APIキーはバックエンドの `pm_backend/.env` の環境変数でのみ管理する。
- APIキーを画面、ログ、仕様書、Git、チャットに出力しない。
- DeepSeekのモデルは画面で選択できるが、バックエンドが許可したモデルIDだけを受け付ける。

## 5. AI用DB辞書の利用区分

| 区分 | 意味 | AIの扱い |
|---|---|---|
| A: 利用許可 | 定義・関連・集計方法を確認済み | 規約に登録した集計関数から参照可 |
| B: 伏字化利用 | 個票を分析する必要がある | 伏字化・最小化を実装後に限定参照可 |
| C: 定義確認待ち | 数量や業務上の意味が未確定 | AI分析・外部送信とも不可 |
| D: 機密/運用設定 | 認証、連絡先、権限、設定、添付など | AI参照・外部送信とも不可 |

## 6. 現在の利用許可データ（区分A）

### 6.1 基本マスタ

| モデル（テーブル） | 主な項目 | 関連 | AI利用目的 | 外部送信 |
|---|---|---|---|---|
| `masters.Product`（`m_product`） | `product_code`, `product_name`, `category`, `unit`, `line`, `process`, `is_active` | ライン、工程、BOM、実績、需要 | 品番・品名・工程の特定 | 品番・品名は必要時のみ。個人情報は含めない |
| `masters.Line`（`m_line`） | `line_code`, `line_name`, `line_type`, `lead_time_days` | 工程、需要、進度、実績 | ライン別集計の軸 | 許可 |
| `masters.Process`（`m_process`） | `process_code`, `process_name`, `line`, `management_unit` | 製品、実績、仕損、中断 | 工程別分析の軸 | 許可 |
| `masters.CalendarDay`（`m_calendar_day`） | `target_date`, `is_working_day`, `work_minutes` | カレンダ、ライン、仕入先 | 稼働日・期間判定 | 許可 |

`masters.Customer` と `masters.Supplier` は名称・コード照会に限りサーバー内で参照する。外部APIへ名称を送る場合は、4.2の一時IDに置換する。`Supplier.contact_person`、`phone_number`、`order_email` は区分Dであり、参照・送信禁止とする。

### 6.2 生産実績

| モデル（テーブル） | 主な項目 | 関連 | 数値定義 | AI利用 |
|---|---|---|---|---|
| `production.ProcessRealtimeRecord` | `timestamp`, `record_type`, `qty`, `line`, `process`, `product`, `product_code`, `operator_name` | 製品、ライン、工程、仕損 | `record_type='PRODUCTION'` の `qty` 合計を生産実績とする。仕入の入荷実績は `record_type='PURCHASE'` で保存されるため含まれない（区別前の2026年9月は `PRODUCTION` の数量の46%が仕入分だった）。品番を質問で指定した場合は `product_code` の完全一致で絞り込む | 日別・工程別・品番別の生産数。作業者別は伏字化利用 |
| `production.LaserActual` / `LaserActualDetail`（`t_laser_actual` / `t_laser_actual_detail`） | `work_date`, `operator_action`, `detail_type`, `product_code`, `total_qty` | レーザー実績ヘッダ、品番別明細、製品、工程 | 生産実績照会のレーザータブと同じく、`operator_action='END'` かつ `detail_type='COMPONENT'` の `total_qty` を品番別生産数とする。START・PAUSE・未終了の明細は含めない | 品番指定時にレーザー実績があれば、`ProcessRealtimeRecord` と合算せずレーザー実績を正規根拠にする |
| `production.LineRealtimeRecord` | ライン、工程、製品、数量、記録時刻 | ライン、工程、製品 | ライン実績として登録された数量。ProcessRealtimeRecordとの二重集計を禁止 | 定義差分確認後に限定利用 |
| `production.ProductionOrder` / `ProcessActual` | 製造指示、工程実績 | 製品、工程、ルーティング | 指示・実績の意味を個別仕様で確認する | 区分C。将来の指示対実績分析候補 |

### 6.3 仕損・品質

| モデル（テーブル） | 主な項目 | 関連 | 数値定義 | AI利用 |
|---|---|---|---|---|
| `quality.ScrapRecord`（`t_scrap_record`） | `plan_date`, `event_type`, `disposition_status`, `qty`, `return_qty`, `reason`, `occurrence_process`, `product` | ライン、工程、製品、実績 | 確定仕損は `event_type='SCRAP'` かつ `disposition_status in ('REJECTED','PARTIAL')`。正味数量は `qty - return_qty` | 理由別・工程別・期間別の正味仕損数量 |
| `quality.ScrapRecordDetail`（`t_scrap_record_detail`） | 仕損、子品目、減算数量、補充状態 | ScrapRecord、製品、BOM | BOM展開明細。親仕損との二重合計禁止 | 区分C。部品影響分析は定義確認後 |

### 6.4 中断・トラブル

| モデル（テーブル） | 主な項目 | 関連 | 数値定義 | AI利用 |
|---|---|---|---|---|
| `production.BrakeLineRecord`（`brake_line_record`） | `plan_date`, `process`, `product`, `product_code`, `operator_action`, `operator_action_reason`, `qty` | 工程、製品、ライン | 生産数は`operator_action in ('END','PAUSE')`の`qty`合計（作業区間ごとに終了・中断時点の加工数を登録するため重複しない。生産実績照会・`LineBacklog.actual_qty`と同じ定義）。中断・強制終了は`operator_action in ('PAUSE','TEMP_END')`のレコード件数 | 品番指定時のブレーキ生産数、理由別・工程別の中断件数 |

作業者ユーザーと作業者名は外部送信前に伏字化する。

### 6.5 残業

| モデル（テーブル） | 主な項目 | 関連 | 数値定義 | AI利用 |
|---|---|---|---|---|
| `overtime.OvertimeApplication`（`t_overtime_application`） | `work_date`, `application_type`, `hours`, `midnight_hours`, `team`, `status`, `applicant` | 組織、ユーザー、承認ログ | `application_type='overtime'` かつ提出済み以降の対象状態について、`hours + midnight_hours` を残業申請時間として合算 | グループ別・期間別集計。個人別は伏字化利用 |
| `overtime.OvertimeApprovalLog` | 申請、承認者、役割、状態、コメント | 残業申請、ユーザー | 承認経過の履歴 | 区分B。コメント・氏名は伏字化必須 |

残業申請時間は打刻実績ではない。個人間比較・順位付けは禁止する。

### 6.5-2 仕入（入荷実績）

| ビュー | 列 | 有効条件 | AI利用 |
|---|---|---|---|
| `v_ai_purchase_receipt`（`ai/0012`で作成、`ai/0013`で抽出条件を変更） | `id`, `arrival_date`, `registered_at`, `supplier_id`, `line_id`, `product_id`, `product_code`, `product_name`, `qty`, `process_id`, `input_source` | `t_process_realtime_record` のうち `record_type='PURCHASE'` の行だけ。仕入れ実績照会画面と同じ定義 | 仕入画面・本社横断から読み取り専用SQLで、仕入先別・品番別・日別の入荷数を集計する |

- 入荷数量は `qty`、入荷日は `arrival_date`（`event_data.arrival_date`）。`arrival_date` は実際に入荷した日、`registered_at` はシステムへ登録した日時。検収（`PURCHASE_RECEIVING`・`PURCHASE_RECEIVING_MOBILE`）は入荷時にその場で登録するので両者は同じ日になるが、仕入れ実績入力（`PURCHASE_ACTUAL_INPUT`）は後から入力できるので異なることがある。入荷の日別・期間集計は必ず `arrival_date` を使う（2026-09-30時点では全2,531件が実績入力で、うち34件は入荷日と登録日が異なる）。
- `event_data` に入っているのは `source`・`line_id`・`supplier_id`・`arrival_date` だけで、個人情報は含まない。
- 仕入先名（`m_supplier.supplier_name`）は外部AIへ送る直前に一時ID（仕入先N）へ伏字化される。連絡先の列は従来どおり個人情報扱い。
- 仕入計画・入荷予定（`LineBacklog` の購買・外作ライン）と、在庫/残量・仕入れ進度（専用計算）はまだ対象外。

### 6.5-3 出荷（出荷実績）

| ビュー | 列 | 有効条件 | AI利用 |
|---|---|---|---|
| `v_ai_shipment`（`ai/0014`で作成） | `id`, `shipment_date`, `product_code`, `product_id`, `product_name`, `customer_code`, `ship_to_code`, `quantity`, `trip_allocation_id`, `remark_text` | `t_shipment_actual` 全行。製品は品番コードで `m_product` と結ぶ（`t_shipment_actual.product_id` は全行NULLのため） | 出荷画面・本社横断から読み取り専用SQLで、品番別・納入場別・日別の出荷数を集計する |

- 出荷数量は `quantity`、出荷日は `shipment_date`。日別・期間集計は `shipment_date` を使う。
- `customer_code`（得意先コード）・`ship_to_code`（納入場コード）はコードであり個人情報ではないため、全利用者に公開する。受注側（`m_customer.customer_code`・`t_order_line.ship_to_code`）も同じ扱いに変更した（得意先名・`customer_id` は従来どおり個人情報区分）。備考は列名 `remark` が個人情報の伏字化対象のため、ビューでは `remark_text` とする。
- `trip_allocation_id`（出荷便割付ID。なければNULL）と `remark_text`（システムが書く便の割付情報。例: `[TRIP_ACTUAL]54:576|PD=2026-07-22:42`）もAIへ渡す。`remark_text` は業務メモではない。
- 2026-10-01時点の開発DBでは488行すべてがクボタ（得意先コード000196）向け。本番の内容は未確認のため、TABLE_NOTES の「現在はクボタ向けのみ」は本番確認後に見直す。
- 出荷計画・便の進捗と、在庫・進度はまだ対象外。

### 6.6 受注（ルーティング未設定の注文品）

| モデル（テーブル） | 主な項目 | 有効条件 | AI利用 |
|---|---|---|---|
| `orders.OrderLine`（`t_order_line`） | `product_code`, `quantity`, `due_date`, `order_type`, `product`, `order` | `order.status='OPEN'`、製品あり、有効な`Routing`なし、画面既定では納期が90日前以降 | 「ルーティング未設定の注文品」画面と同じく品番ごとに1件へ絞った件数・品番・納期を参照する |
| `masters.Routing` | `product`, `is_active` | 同一製品に`is_active=True`が1件でもあれば対象外 | 未設定判定だけに利用する |

受注明細の数量は、品番ごとに画面表示対象として選ばれた代表明細の数量であり、全受注明細の合計ではない。得意先名、受注番号、顧客発注番号、備考は外部APIへ送信しない。

## 7. 関連図（現在許可する範囲）

```text
Product ──< BOM ──< BOMItem >── Product（子品目）
   │                 │
   ├── ProcessRealtimeRecord ──> Process ──> Line
   ├── LaserActualDetail ──> LaserActual ──> レーザー設備
   ├── ScrapRecord ────────────> Process / Line
   └── BrakeLineRecord ────────> Process / Line

Department ──< OvertimeApplication >── User
```

分析では、同じ事実を複数の実績テーブルから合計しない。特に生産実績は、質問ごとに規約で指定した正規データソースだけを使う。

## 8. 数値・期間の共通定義

- 日付の業務境界は午前8時。8:00より前の入力は前業務日として扱う画面・処理があるため、各集計関数は既存業務ロジックに従う。
- 生産数、仕損数、在庫数、進度、需要数、計画数は同じ「数量」でも意味が異なる。回答では対象モデル・項目・期間を根拠として示す。
- 進度の需要データは `production.LineDemand` を正規データソースとする。`LineBacklog.order_qty` や `demand_qty_plan` を代替利用しない。
- `LineBacklog` の `sequence_no=0` は需要専用行、`sequence_no>0` は計画専用行である。両者を混在させた合計や実績解釈をしてはならない。
- 在庫・進度・計画在庫の計算は既存の専用計算ロジックに従う。AIが独自式で再計算してはならない。

## 9. 利用保留または禁止のデータ領域

以下はモデルが存在しても、初版では区分CまたはDとする。

| 領域 | 区分 | 理由 |
|---|---|---|
| 受注・出荷・便計画 | C（一部A） | 受注は「ルーティング未設定の注文品」だけ区分A。その他は納期・数量・顧客との関係、正規の進捗定義を領域ごとに確認する必要がある |
| 購買・発注提案・仕入先納入 | C（一部A） | 入荷実績（`v_ai_purchase_receipt`）だけ区分A。仕入計画・入荷予定・発注提案・在庫/進度は定義確認後に追加する |
| 在庫・棚卸・引当・進度 | C | 数量の意味と再計算責務が複雑なため、専用仕様を確認後に追加する |
| 設備点検・品質チェックシート・画像・添付 | D | 添付、画像、作業記録の送信可否を別途決める必要がある |
| ユーザー、権限、承認、通知、通話、認証 | D | 個人情報・認証情報・通信内容を含むため |
| システム設定、APIキー、メール送信設定 | D | 運用・認証情報のため |

## 10. 新しいデータ領域を追加する手順

1. 対象モデル、項目、テーブル間の関連をモデル定義から記録する。
2. 既存仕様書と実データで、数量・状態・日付の業務上の意味を確認する。
3. AIが使う集計関数、入力条件、出力項目、二重計上防止条件を本書へ追記する。
4. 外部APIへ送る項目、伏字化対象、禁止項目を決定する。
5. `ai/services/chat_service.py`（または関連する`ai/services/*.py`）に読み取り専用の専用関数として実装する。API入口の `ai/views.py` には業務ロジックを置かない。
6. 代表データで根拠・数量・期間を検証してから画面へ公開する。

未確認のまま、モデル名だけを根拠にAIの参照範囲へ追加してはならない。

## 10-1. AI用DB辞書の読み取り専用SQL

DeepSeekは、専用集計ツールだけでは回答できない場合に限り、画面起点で許可された区分Aのテーブル・列を用いた`SELECT`文を作成し、`pm_ai_reader`で実行できる。

- 許可するのは`SELECT`一文のみ。複数文、コメント、ワイルドカード（`*`）は拒否する。
- `INSERT`、`UPDATE`、`DELETE`、`CREATE`、`ALTER`、`DROP`、`TRUNCATE`、`SET`、`SHOW`、`CALL`、ロック取得、ファイル出力は常に拒否する。
- 氏名、連絡先、受注番号、顧客発注番号、備考、ロット番号、作業者・申請者・承認者の列は、通常のSQL辞書から除外する。AI設定で個人別集計を許可し、画面の個人別残業集計権限を持つ利用者に限り、個人情報列として参照できる。DeepSeekへ送る値は一時IDまたは伏字に置き換え、回答時にだけ復元する。
- 行数はAI設定の「外部送信する最大集計行数」以下とし、`LIMIT`がない場合はサーバーが付与する。
- 画面別に許可したテーブルを超える参照は拒否する。購買・出荷・在庫は、定義確認が完了するまでSQL照会を公開しない。
- このツール自体の有効化・無効化と、外部AI（DeepSeek）への送信可否は、2-1 の `AIToolPolicy`（画面ごと）で管理する。無効化した画面・プロバイダの組み合わせでは呼び出せない。

## 11. 実装状況

| 規約 | 現状 | 次の対応 |
|---|---|---|
| 更新・削除・DDL・管理SQLの拒否 | 実装済み | `sql_queries.py`のFORBIDDEN_SQLで常に拒否。追加時はキーワードを本書とコードへ同時追記 |
| AI用DB辞書の読み取り専用SQL（10-1） | 実装済み | `execute_readonly_sql`を`pm_ai_reader`（SELECT権限のみ、接続元IP限定）経由で実行。画面別ホワイトリスト外・書込み系・ワイルドカードは拒否 |
| 運用設定管理画面（2-1） | 実装済み | `/settings/ai`（権限`settings.ai`）でプロバイダ・ツール有効化・データ送信方針・ナレッジ登録を管理 |
| `ai.chat`・個人別残業のサーバー側権限検証（2-2） | 実装済み | `AIChatAPIView`（旧`ProductionAIDemoView`）に`IsAuthenticated`を追加し、`ai.chat`と`overtime.personal_summary`は実効権限をサーバー側でも確認する。あわせて`accounts.models.UserPermission.RESOURCE_CHOICES`に不足していた`ai`/`ai.chat`/`settings.ai`/`overtime.personal_summary`を追加した（未登録だと実効権限に一切現れず、一般ユーザーが権限を持てなかったため） |
| DeepSeekモデル許可リスト | 実装済み | モデル追加時は本書とコードを同時更新 |
| 生産・仕損・中断・残業の集計 | 実装済み | DeepSeekが品番検索・読み取り専用集計ツールを選択し、数値根拠を回答に継続表示 |
| 個人名などの一時伏字化 | 実装済み | PMに登録されたユーザー・作業者名・得意先名・仕入先名を一時IDへ置換する。個人別残業は `overtime.personal_summary` を持つ画面でだけ応答時に復元する。連絡先は復元しない |
| 受注・在庫・購買・出荷の分析 | 受注のルーティング未設定品だけ実装済み | その他の領域は辞書・集計関数を確認後に追加 |
