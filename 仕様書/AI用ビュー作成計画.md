# AI用ビュー作成計画

## 1. 目的

PM本体テーブルをAIへ直接公開せず、業務上の意味・数値定義・公開フィールドを固定した`v_ai_...`ビューだけをAI分析に使用する。

ビューはデータを複製しない。PM本体の最新データをリアルタイムで参照し、更新・削除の同期漏れを防ぐ。AIが参照するビューは、`pm_ai_reader`へ`SELECT`だけを付与する。

本計画は[AI分析基盤仕様書](AI分析基盤仕様書.md)および[AI運用規約・AI用DB辞書](AI運用規約・AI用DB辞書.md)に従う。

## 2. 現在のビュー

| ビュー | 用途 | 状態 |
|---|---|---|
| `v_ai_purchase_receipt` | 仕入の入荷実績を平坦な列構成で参照する | 作成済み |
| `v_ai_shipment` | 出荷実績と品番情報を結合して参照する | 作成済み |

既存ビューは、開発・本番ごとに定義者、実行可否、`pm_ai_reader`の権限を確認する。開発DBの`v_ai_purchase_receipt`で発生しているエラー1449は、追加ビュー作成前に修正する。

## 3. 作成対象と優先順位

### 優先0：マスタビュー（実績ビューより先に作成する）

実績ビューは品番ID・工程IDなどのコードだけを持ち、名称や属性はマスタビューで引く。そのため、マスタビューを実績ビューより先に作成する（BOSS指示）。

| 候補 | 元テーブル | 状態 |
|---|---|---|
| 品番 | `m_product` | 未着手（BOSSが作成対象と順序を指定） |
| 工程 | `m_process` | 同上 |
| ライン | `m_line` | 同上 |
| 仕入先 | `m_supplier` | 同上 |
| 得意先 | `m_customer` | 同上 |
| 稼働カレンダ | `m_calendar_day` | 同上 |
| BOM（親品番のヘッダ） | `m_bom` | 同上（BOSS指示 2026-10-10） |
| BOM明細（子品番・員数） | `m_bom_item` | 同上 |
| ルーティング（ヘッダ） | `m_routing` | 同上（BOSS指示 2026-10-10） |
| ルーティング工程 | `m_routing_step` | 同上 |
| ルーティング工程の材料 | `m_routing_step_material` | 同上（BOSS指示 2026-10-10。作成する） |
| ラインの所属グループ（ライン×グループの対応） | `accounts_unit_line_mapping` | 同上（BOSS指示 2026-10-10。ライン編集画面の「所属グループ」。`m_line`には列がないため、別のビューにする。全フィールドの一覧を作成し、BOSSが公開列を決める） |

BOM・ルーティングは、ヘッダと明細が別テーブルのため、1テーブル1ビューの原則に従い、別々のビューにする。ヘッダと明細の結合は、AIがビュー同士で行う（結合キーは各ビューの説明に書く）。**ただし BOM は例外**：BOM明細は、明細（`m_bom_item`）を主にしてヘッダ（`m_bom`）を `LEFT JOIN` した1つのビュー `v_ai_bom_item` にする（BOSS承認 2026-10-11。§25）。ヘッダ単独のビューは作らない。ルーティングに同じ方式を使うかは、別に決める。

ユーザー関連（BOSS指示 2026-10-10。作成する）

| 候補 | 元テーブル | 状態 |
|---|---|---|
| ユーザー | `auth_user`（Django標準） | 未着手 |
| ユーザープロフィール（部署・役職） | `accounts_userprofile` | 未着手 |
| 部署 | `accounts_department` | 未着手 |

目的（BOSS指示 2026-10-10）：作業者別の実績、部署別の集計。

ユーザーは、パスワード（ハッシュ）・メールアドレス・個人名などを持つ。公開する列は、全フィールドの一覧からBOSSが決める。パスワード・認証情報・連絡先は、公開案から外す。個人名を公開する場合は、外部AIへ送る前に一時IDへ置換する（残業の個人別ビューと同じ扱い）。

マスタビューができた後、`SCREEN_SQL_TABLES`が許可している元テーブル（`m_supplier`・`m_product`・`m_line`・`m_calendar_day`）をビューへ置き換える。置き換えは既存動作の変更になるため、実施前にBOSSへ報告し、承認を得る。

### 優先1：正規実績・確定実績

| 候補ビュー | 対象 | 作成方針 |
|---|---|---|
| `v_ai_process_production_actual` | `t_process_realtime_record`の工程生産実績 | `record_type='PRODUCTION'`だけを対象にし、仕入実績を含めない |
| `v_ai_laser_production_actual` | レーザー実績 | レーザー画面と同じく、終了済み構成部品明細だけを対象にする。`t_laser_actual` に `line_id` / `process_id`（保存時に L0801 / 0801 のマスタ行IDを設定。補完完了までは NULL あり）を追加したため、ビューから直接出せる（公開可否はBOSS決定。本変更ではビューを変更していない） |
| `v_ai_brake_production_actual` | ブレーキ・スポット実績 | `END`・`PAUSE`の数量だけを生産数として扱う |
| `v_ai_scrap_confirmed` | 確定仕損 | `event_type='SCRAP'`かつ確定・一部使用可の正味数量だけを対象にする |
| `v_ai_interruption` | 中断・強制終了 | `PAUSE`・`TEMP_END`の件数と理由を対象にする |

生産実績は、工程実績・レーザー実績・ブレーキ実績を無条件に`UNION`または合計しない。質問・工程ごとに正規データソースを選び、同じ事実を二重計上しない。

仕損担当者は `t_scrap_record.operator_login_id` / `cause_login_id` / `reporter_login_id`（username、NULL可）を将来の仕損ビューで公開する計画。三者JSONや姓名を分析元にしない。`username` は作成後に変更できない（API・管理画面で拒否。`仕様書/ユーザー名変更禁止実装計画.md`）ため、ログインIDで過去の記録とユーザーを結合できる前提とする。本単位では列追加・保存までで、AIビュー作成・公開は行わない。

### 優先2：残業

| 候補ビュー | 対象 | 作成方針 |
|---|---|---|
| `v_ai_overtime_summary` | 残業申請のグループ別・日別集計 | 時間外・休日出勤の承認対象状態だけを対象にし、個人名を含めない |
| `v_ai_overtime_personal` | 個人別残業集計 | `overtime.personal_summary`権限を持つ利用者に限定して使用する。外部AIへ送る場合は一時IDへ置換する |

残業は申請時間であり、打刻実績ではない。

なお、残業の個人別について、「個人の順位付け・評価・査定に使用しない」とした従来の規定は、BOSS指示により取り下げた（2026-10-10）。

### 優先3：マスタ・将来領域

品番・工程・ライン・仕入先・得意先・稼働カレンダ・BOM・ルーティングのマスタビューは、優先0で先に作成する。仕入計画、在庫、進度、受注全体、製造指示、BOM展開明細は、数値定義が確定するまで作成しない。

## 4. 各ビューの作成前確認

### 4.1 ビュー設計の原則（BOSS決定）

1. **基本は1テーブル1ビュー。** 1つのビューは1つの元テーブルから、必要な列だけを取得する。1つの元テーブルに複数のビューを作ってよい（例：記録タイプ別）。1ビューでは都合が悪い場合は、作成前に理由をBOSSへ報告する。
2. **ビューの中で結合してよいのは、マスタの属性を付けるときだけ。** 例：品番IDだけの実績に、品番コード・品名を付ける。
   - 結合先はマスタとし、結合キーはマスタの主キーにする。
   - `LEFT JOIN`を使い、実績の行数を増減させない。作成時に、元テーブルとビューの件数が一致することをDBで確認する。
   - 公開してよい列だけを結合する。個人名・連絡先を持つ列は結合しない。
   - **例外（BOSS承認 2026-10-11。§25）**：BOM明細のビュー `v_ai_bom_item` は、明細（`m_bom_item`）を主テーブルにし、ヘッダ（`m_bom`）を `bom_id` の主キーで `LEFT JOIN` する。ヘッダは「明細に付ける属性」であり、結合キーは結合先の主キーなので、行数は明細と同じ（行数が増えない）。1テーブル1ビューの原則の例外とする。
   - 結合は「してよい」であり、必須ではない。§8.3（2026-10-08）のとおり、AIにビュー同士を結合させる方式も併用できる。どちらにするかは、ビューごとにBOSSが決める。
3. **実績同士を結合するビューは作らない。** 実績を比べる分析（入荷と出荷など）は、結合せず、同じ列に揃えて`UNION ALL`し、種類ごとに`SUM(CASE WHEN)`で並べる。結合すると目的ごとにビューが増えるため。
4. **対象行の絞り込み（`WHERE`）は、1つの元テーブルの中でなら付けてよい。** 例：`record_type='PRODUCTION'`。仕入実績の混入を、ビューの側で防ぐ。
5. **元テーブルの全フィールドを一覧にし、公開するかどうかはBOSSが決める。** 一覧には、列名・型・業務上の意味・公開案を載せる。ビューに含める列は、BOSSが公開と決めた列だけとする。非公開の列は、ビューに含めない。
6. **マスタビューを先に作る。** 実績ビューは、その後に作る。
7. **列の説明（AI用DB辞書・`ANALYSIS_VIEWS`の説明）は、各仕様書で意味を確認してから書く（BOSS指示 2026-10-10）。** 列名や項目名からの推測で書かない。仕様書に定義がない列は「意味は未確認」と書く。確認した出典（仕様書名・行）は、確認明細または各ビューの節に残す。

8. **ビューのマイグレーションは、標準SQLだけで書く（BOSS承認 2026-10-10）。** 将来、MySQLからPostgreSQLへ変更し、AI検索もDBへ直接アクセスしない予定のため。バッククォート・`DEFINER`・`SQL SECURITY`・DBの修飾など、MySQL固有の記法はマイグレーションに入れない。定義者と権限は、DBごとに書き方が違うため、マイグレーションに含めず、別の手順SQL（開発・本番とも、実行はBOSS）にする。
9. **ビューの定義者は、必ず専用ユーザー `pm_ai_view_owner` にする（BOSS指示 2026-10-10）。** `root` など、マイグレーションを実行したDBユーザーを定義者のまま残さない。
   - マイグレーション（`migrate`）でビューを作ると、定義者は実行したDBユーザー（`root` 等）になる。そのため、`migrate` の**直後に**、次の2つを行う。
     1. `pm_ai_view_owner` に、そのビューが読む元テーブルの**公開列だけ**の `SELECT` を、列単位で付与する（`GRANT SELECT (列, …) ON 元テーブル TO pm_ai_view_owner@localhost`）。
     2. `CREATE OR REPLACE DEFINER = pm_ai_view_owner@localhost SQL SECURITY DEFINER VIEW …` で、ビューを作り直し、定義者を付け替える。
   - ビューを新規に作る・変更するたびに、同じ手順を行う。手順SQLは、ビューごとに、各ビューの節（例 §9.3）へ書く。
   - 確認：`information_schema.VIEWS` の `DEFINER` が `pm_ai_view_owner@localhost` であること、`pm_ai_reader` の接続でビューが読めること、非公開列が読めないこと。
   - 理由：公開列だけに権限を絞る設計を効かせるため。定義者が存在しないとエラー1449でビューが読めなくなるため、`root` のように環境で変わるユーザーを使わない。
   - 手順は、`python manage.py setup_ai_views --apply`（管理者で実行）で行える。手順SQL（§9.3・§14.1・§16.1・§19.1）は、コマンドが実行するSQLの記録として残す（§20）。
   - 実施状況：`v_ai_product` は開発DBで実施済み（2026-10-10。定義者 `pm_ai_view_owner@localhost`、公開32列の列権限（その後、2026-10-10 BOSS判断で30列へ修正。0037・§9.3参照）、`pm_ai_reader` の接続で件数2,850・有効2,808、`image_url` は読めないことを確認）。本番は未実施（BOSSが実行）。
   - PostgreSQLへ移行した後は、定義者の考え方を「所有者を専用ロールにする」に読み替える（§9.3参照）。

### 4.1-1 仕様書で確認できた品番の列の意味（2026-10-10 調査）

| 列 | 仕様書にある意味 | 出典 |
|---|---|---|
| `order_lot_min`・`order_lot_multiple` | 発注量＝不足数を発注倍数の倍数に切り上げ、最小発注数未満なら最小発注数にする。`order_qty = ceil(不足数 / 倍数) × 倍数`、`order_qty = max(order_qty, 最小発注数)` | 自動発注提案仕様書.md:211-212 |
| `transfer_destination` | 移動先。値の表示順は 社内塗装・CWL・興和・直納・社内ライン・その他/未設定 | 自動納入リスト送信仕様書.md:87,91 |
| `category` | 値は ASSEMBLY・SINGLE・MATERIAL・PURCHASED・OUTSOURCED・UNKNOWN の6種。各値の意味の定義は見つからない（受注展開時の既定は PURCHASED＝購入品） | ER_diagram_v3.md:34、受注管理仕様書.md:777 |
| `is_virtual_set` | 仮想セット品番＝連産品。子実績を展開する | 仕入実績record_type分離仕様書.md:37 |
| `is_final_product`・`is_line_final_product` | 受注展開では最終品かどうかでリードタイムの扱いを分ける。ライン最終品は、前工程需要で後ラインの親が無い日の代替に使う。定義の文章は見つからない | 受注展開仕様書.md:418、前工程需要計算仕様書.md:93-101 |
| `management_unit`（品番） | 品番の管理区分としての定義は見つからない（工程の管理単位は DAY=日単位管理・MINUTE=分単位管理） | モデル定義のみ |
| `stock_location`・`identification_code`・`processing_area`・`size_*`・`specific_gravity` | 定義の文章は見つからない | — |

### 4.2 作成前確認の項目

各ビューは、次の項目を文書化し、BOSSの承認後に作成する。

| 確認項目 | 内容 |
|---|---|
| 業務目的 | AIが何を分析・説明するためのビューか |
| 元テーブル | 参照するテーブルと結合条件 |
| 対象行 | ステータス、レコード種別、期間などの抽出条件 |
| 数値定義 | 数量・件数・時間の正式な算出方法 |
| 公開フィールド | AIへ見せる列と列の業務上の意味 |
| 非公開フィールド | 連絡先、認証情報、未承認の自由記述などの除外対象 |
| 個人情報 | 利用権限、一時ID化、外部AI送信可否 |
| 検証方法 | 既存画面・DB実データとの件数、数量、期間の照合方法 |

得意先・仕入先は名称ではなくコードを原則とする。例として、クボタは`000196`、ホウダテクニカルは`000180`である。

## 5. 実装手順

### 5.1 定義作成

1. 対象モデルと既存画面の集計ロジックを確認する。
2. 元テーブル、結合条件、対象行、数値定義、フィールド一覧を作成する。
3. 代表的な実データで、既存画面と件数・数量・対象期間を照合する。
4. BOSSがビュー定義とAI公開範囲を承認する。

### 5.2 マイグレーション

1. `pm_backend/apps/ai/migrations/`へ新規マイグレーションを作成する。
2. `CREATE OR REPLACE VIEW v_ai_... AS ...`でビューを定義する。
3. ビューの定義者には、開発・本番に常に存在する専用サービスユーザーを使用する。`root`を定義者に使用しない。
4. ロールバック用に`DROP VIEW IF EXISTS v_ai_...`または直前のビュー定義を用意する。
5. 開発DBへ適用し、`SELECT`実行と既存画面との照合を行う。

### 5.3 AI公開設定

1. `pm_ai_reader`へ、対象`v_ai_...`ビューの`SELECT`だけを付与する。
2. 元テーブルへの`SELECT`、更新、削除、DDL、ストアドプロシージャ実行権限を持たないことを確認する。
3. `pm_backend/apps/ai/services/sql_queries.py`のAI用DB辞書へ、ビュー名、公開フィールド、業務上の意味を追加する。
4. `SCREEN_SQL_TABLES`へ、画面起点ごとに許可するビューだけを追加する。
5. [AI運用規約・AI用DB辞書](AI運用規約・AI用DB辞書.md)と[AIチャット仕様書](AIチャット仕様書.md)を更新する。

### 5.4 本番反映

1. 本番DBに、ビュー定義者ユーザーと`pm_ai_reader`の権限が存在することを確認する。
2. マイグレーションを適用する。
3. `SHOW CREATE VIEW`と`SHOW GRANTS`で、ビュー定義と権限を確認する。
4. `pm_ai_reader`でビューが読め、元テーブルへの直接参照が拒否されることを確認する。
5. PM画面の既存業務処理が影響を受けないことを確認する。

## 6. 検証項目

- 既存画面とビューの件数・数量・対象期間が一致する。
- 仕入実績が生産実績へ混入しない。
- 複数実績ソースを合計して二重計上しない。
- `pm_ai_reader`はビューだけを`SELECT`できる。
- ビューからの`INSERT`、`UPDATE`、`DELETE`はできない。
- 定義者が存在せずエラー1449になる状態がない。
- 個人情報・連絡先・認証情報・未承認の自由記述が公開フィールドに含まれない。
- 外部AIへ送る値は、運用規約に定めた一時ID化・送信方針に従う。

## 7. 完成条件

- 優先1の各ビューについて、業務定義・公開フィールド・検証結果が承認済みである。
- 追加ビューはAI用DB辞書・画面別許可リスト・運用規約へ反映済みである。
- 開発・本番で、AI用ビューの実行可否と`pm_ai_reader`の権限を確認済みである。
- AI分析画面は、承認済みの`v_ai_...`ビューだけを使用できる。

## 8. 仕入先マスタのビュー `v_ai_supplier` の作成前確認（案。2026-10-08。**§17に置き換える**。以下は別セッションの古い草案で、設計原則§4.1と食い違う点がある）

実機の安定性の評価（試験T8「9月の入荷を仕入先ごとに集計して」）で、結果の表が「仕入先ID」（`supplier_id`＝`m_supplier.id`。データベースの内部の番号）だけになった。現場が分かるのは、仕入先名か、せめて仕入先コード。入荷実績ビューには、仕入先の列が`supplier_id`しかなく、仕入先マスタのビューも、まだない。§3 優先3「マスタ・将来領域」の、仕入先を、分析画面で必要になったため、追加する。

| 確認項目 | 内容 |
|---|---|
| 業務目的 | AIが、仕入先をコード・名前で、分析・説明できるようにする（仕入先ごとの入荷の集計の、表示に、内部のIDを出さない）。仕入先の一覧・種類別の件数にも使う |
| 元テーブル | `m_supplier`（29行。`supplier_code`は一意・空なし。入荷に出る仕入先6社は、すべて、マスタにある＝孤立なし） |
| 対象行 | 全行（絞り込みなし）。ビューは、データを複製しない |
| 数値定義 | なし（マスタ。件数は、行数） |
| 公開フィールド | `id`（仕入先の内部ID。他のビューとの結合用）、`supplier_code`（仕入先コード）、`supplier_name`（仕入先名）、`supplier_type`（`purchase`=購入先・`outsource`=外作先・`both`=両方） |
| 非公開フィールド | `order_email`（発注先メール）、`contact_person`（担当者名）、`phone_number`（電話番号）、`calendar_id`（カレンダーのID。分析に不要） |
| 個人情報 | 仕入先名は会社名で、連絡先（メール・担当者・電話）は、含めない。結果の画面には出るが、**AIへは、列名と型だけを送り、値は送らない**。外部AIへ送る目的文の、名称→コード置換は、従来どおり |
| 検証方法 | `m_supplier`の行数（29）と、ビューの行数が一致。コードの一意性。入荷実績ビューの仕入先別の集計（9月: 仕入先16=20,259・仕入先8=11,270）を、コード・名前つきで、照合。`pm_ai_reader`でビューが読め、元テーブルの直接参照は、ビューだけに絞った権限では、拒否される |

### 8.1 あわせて変更するもの（案）
1. **`v_ai_purchase_receipt`に、`supplier_code`・`supplier_name`を追加**（`m_supplier`と`supplier_id`で、左結合。仕入先がない行も、残す。入荷の行は、増えない）。AIが、ビューどうしを結合しなくても、仕入先のコード・名前を使える（小さいモデルでも、取り違えにくい）。
2. **AIへの指示・対応表**: 「仕入先・外作先」→`supplier_code`・`supplier_name`。仕入先ごとの集計は、コードと名前を出し、**内部のID（`*_id`）は、結果に出さない**（品番の「品番→製品名→数量」と同じ考え方）。
3. **ビューの定義者`pm_ai_view_owner`の権限**: `m_supplier`の`id`・`supplier_code`・`supplier_name`・`supplier_type`の列単位の`SELECT`を追加（連絡先の列は、付けない）。
4. **AI用DB辞書**（`sql_queries.py`の`BASE_SQL_SCHEMA`・`TABLE_NOTES`）・列の型・`ANALYSIS_VIEWS`の説明・`SCREEN_SQL_TABLES`（仕入画面の許可ビューへ`v_ai_supplier`）・仕様書・運用規約を更新。
5. 手順は、§5のとおり: マイグレーションで`CREATE OR REPLACE VIEW`（定義者は`pm_ai_view_owner@localhost`。rootを使わない）→開発で適用・照合→本番は、SQLを用意して、BOSSが実行（権限の付与・ビューの作成。本番の変更は、承認と、バックアップが必要）。

### 8.2 BOSSに決めてほしいこと
- 公開する列の範囲（上の4列でよいか。**仕入先名を、公開するか**。§4 の原則は「名称ではなくコード」だが、現場が分かるのは名前のため、コードと名前の両方を、おすすめする）。
- 入荷実績ビューへ、`supplier_code`・`supplier_name`を足すか。
- 得意先・品番・ライン・工程など、他にも、内部のIDだけの列があるか（現状の入荷実績ビューの`line_id`・`process_id`は、ラインと工程のIDで、コード・名前の列が、ない）。

### 8.3 設計メモ（BOSS指示 2026-10-08。「ビュー作成は大きなプロジェクトのため、別に検討する」。コードの変更なし）

**決定したこと**
- `v_ai_supplier`の公開列は、`id`・`supplier_code`・`supplier_name`・`calendar_id`・`supplier_type`。非公開は、`order_email`・`contact_person`・`phone_number`。ビューの定義者`pm_ai_view_owner`の権限も、同じ5列の`SELECT`。
- **`v_ai_purchase_receipt`には、仕入先の列を足さない**。都度、列を足すのは避け、**AIに、2つのビューを結合させる**（入荷の`supplier_id`＝仕入先の`id`）。
- 結合が、小さいモデルで、安定して成功するかは、**試験で、成功率を見て決める**（T8と同じ目的で、数回）。成功率が低ければ、よく使う組み合わせだけ、結合済みの列を足す（併用）。

**AIへの指示の案**
1. 結果には、内部のID（`*_id`）を出さない。仕入先ごとの集計は、コードと名前を出す（品番→製品名と、同じ考え方）。
2. 出したい列が、内部のIDしかないときは、**他のビューに、コード・名前の列がないか、確認する**。
3. 手順を考える前に、**ビューの構造・説明・ビューどうしの関係（結合のキー）を、最初に確認する**。作業の順序は、「①列の意味を読む→②目的の言葉を列に結び付ける→③**ビューどうしの関係を確認する**→④手順を作る」。ビューの説明文に、関係（例: 入荷の`supplier_id`＝仕入先の`id`）を、書く。
4. 分析に必要なビューは、**データ範囲に、すべて入れる**（マスタのビューを選び忘れると、コード生成が、「列がない」と止まる。T2の「納入場名」と同じ型の失敗）。

**機械の安全網の案**
- 結果に出す列が、`supplier_id`などの内部IDだけで、対応するマスタのビューが、データ範囲にないときは、承認の前に、警告を出す（列の言葉の食い違いの警告と、同じ仕組み）。

**留意**
- 仕入先マスタにない仕入先IDの入荷は、今のデータでは0件（入荷の6社は、すべて、マスタにある）。結合の種類（内部結合・左結合）は、重要度が低い。将来、マスタにない行ができても、黙って消えるだけなので、結果の件数を、確認できるとよい。

**別に検討する課題（大きい変更）**
- **日付列のないビュー（マスタ）を扱う**（取り下げの決定: BOSS 2026-10-10。「全ビューに日付列を必須とする」規定を取り下げ、`date_field=None`で全行取得する方式に変更。実装は§11サイクルB）: 従来の仕組みは、すべてのビューが日付列を持つ前提だった（分析案の検証・件数の確認・データの取り出し〔`analysis_data_service`・`analysis_execution_service`〕）。マスタは、期間で絞らず、全行を取得する。
- ビューの作成（マイグレーション）・権限・辞書・画面別の許可リスト・指示・試験・仕様書・運用規約・本番のSQL。

## 9. 品番マスタのビュー `v_ai_product` の作成前確認（案。2026-10-10。BOSSの承認待ち）

マスタビューの最初の1つ。公開する列は、[AIマスタビュー確認明細](AIマスタビュー確認明細.md)のBOSS判断のとおり。

| 確認項目 | 内容 |
|---|---|
| 業務目的 | AIが、品番をコード・名前・分類・寸法・発注条件で、分析・説明できるようにする。実績ビューの品番ID・品番コードから、品名や分類を引く |
| 元テーブル | `m_product` の1つだけ。結合なし（行数2,850） |
| 対象行 | 全行（絞り込みなし）。有効2,808・無効42。無効品番は`is_active`で、AIが絞る |
| 数値定義 | なし（マスタ）。件数は行数。`product_code`は2,850行で重複なし・空なし |
| 公開フィールド（30列。2026-10-10 BOSS判断で`created_at`・`updated_at`を非公開に修正） | `id`、`product_code`、`product_name`、`category`、`unit`、`unit_price`、`standard_lt_days`、`stock_location`、`processing_area`、`line_id`、`process_id`、`next_process_id`、`management_unit`、`is_final_product`、`is_line_final_product`、`is_virtual_set`、`order_lot_min`、`order_lot_multiple`、`is_special_management_material`、`specific_gravity`、`size_length`、`size_width`、`size_thickness`、`transfer_destination`、`model_name`、`identification_code`、`product_group_id`、`used_container_id`、`capacity`、`is_active` |
| 非公開フィールド | `image_url`、`product_name_halfwidth`、`is_phantom`、`self_lt_days`、`created_at`、`updated_at`（BOSS判断。`created_at`・`updated_at`は2026-10-10に追加。BOSSが判断画面で非公開にしていたが、32列で実装・コミットしていたため、0037で修正） |
| 個人情報 | なし（個人名・連絡先・認証情報の列を含まない）。社内AIの列名検査（`SENSITIVE_IDENTIFIER`）に当たる列名もない |
| 検証方法 | ①ビューの行数＝`m_product`の行数（2,850）②`product_code`の一意性③`is_active`の件数（有効2,808・無効42）④`pm_ai_reader`でビューが読め、`m_product`の直接参照が拒否される⑤非公開の6列がビューにない |

### 9.1 未確認・注意
- `unit_price`は2,386行がNULL（単価の入っている品番は464行）。`line_id`は1,833行、`process_id`は2,003行がNULL。AIの説明文に「空の品番がある」と書く。
- `category`は6種（ASSEMBLY 1,015、OUTSOURCED 697、SINGLE 587、PURCHASED 284、UNKNOWN 198、MATERIAL 53）とNULL 16行。各値の業務上の意味は未確認。
- `management_unit`（品番の管理区分）はDAY 787・MINUTE 7・空2,056。工程の管理単位（DAY=日単位管理、MINUTE=分単位管理）と同じ意味かは未確認。
- `unit_price`は金額情報。BOSS判断で公開としたため、公開する。

### 9.2 あわせて変更するもの（案）
1. マイグレーション：`CREATE OR REPLACE VIEW v_ai_product AS SELECT <32列> FROM m_product`（0034。のち0037で30列へ修正）。ロールバックは`DROP VIEW IF EXISTS v_ai_product`。
2. ビューの定義者`pm_ai_view_owner`の権限：`m_product`の列単位の`SELECT`を、32列へ広げる（のち30列へ修正。§9.3）（現在は`id`・`product_code`・`product_name`の3列だけ。既存の`v_ai_shipment`が使用中）。本番では、権限付与のSQLをBOSSが実行する。
3. `pm_ai_reader`へ`v_ai_product`の`SELECT`だけを付与する。
4. AI用DB辞書（`sql_queries.py`）・`ANALYSIS_VIEWS`の説明・`ANALYSIS_COLUMN_TYPES`（開発DBの`SHOW COLUMNS`に合わせる）・`SCREEN_SQL_TABLES`・仕様書・運用規約を更新する。
5. 既存の`v_ai_shipment`（`m_product`を結合している）は、今回は変更しない。

### 9.3 実装の進捗（2026-10-10。generator。検証はevaluator待ち）

**実装済み（コード・文書）**
- `pm_backend/apps/ai/migrations/0034_ai_product_view.py` 新規。`CREATE OR REPLACE VIEW v_ai_product`（32列・別名なし・WHEREなし・結合なし）、ロールバックは`DROP VIEW IF EXISTS v_ai_product`。依存は`ai 0033`と`masters 0085`。`makemigrations --dry-run`は「No changes detected」。
- `sql_queries.py`：`BASE_SQL_SCHEMA`に`v_ai_product`（当初32列。2026-10-10に30列へ修正）、`TABLE_NOTES`に説明を追加（`ai_home`は`BASE_SQL_SCHEMA`の全キーを引くため自動で対象に入る）。
- `AI運用規約・AI用DB辞書.md`に§6.5-4を追加。

**実施していないこと（BOSS実行）**
- 実装時点（2026-10-10）は、`migrate`・ビュー作成・権限付与（GRANT）が未実行だった。**その後、開発DBで実施済み**（BOSS指示。`migrate ai 0034`でビュー作成、列権限の付与、定義者を`pm_ai_view_owner@localhost`へ付け替え。§4.1の9番・§12参照）。本番は未実施。
- 開発で確認済み（読み取りのみ）：マイグレーションのSELECT文は`m_product`に対して実行でき、2,850行・32列を返す。
- **2026-10-10 修正（BOSS承認）**：BOSSが判断画面で`created_at`・`updated_at`を非公開にしていたため、公開列を32列から30列に修正する。`0034_ai_product_view.py`は開発DBに適用済みのため書き換えず（32列の歴史的なSQLのまま）、新規マイグレーション`0037_ai_product_view_remove_dates.py`（`CREATE OR REPLACE VIEW v_ai_product AS SELECT <30列> FROM m_product`。ロールバックは0034の32列の定義へ戻す。依存は`ai 0036`・`masters 0085`で0034と同じ）で30列にする。実データ（開発DB、`pm_ai_reader`接続の読み取りのみ）：`m_product`から30列を読み、全2,850行×30列が`ANALYSIS_COLUMN_TYPES`の型で`_cell`を通る（エラー0）。**開発DBは、0037の`migrate`と手順SQLの実行（2026-10-10、BOSS承認のうえ、私が実行）で、30列に直した**（確認：30列で`created_at`・`updated_at`を含まない、`pm_ai_reader`で件数2,850・有効2,808、定義者`pm_ai_view_owner@localhost`、`pm_ai_view_owner`の`m_product`列権限は30列、`v_ai_shipment`は542件で影響なし）。本番は未反映。

**権限の付与方式の調査結果**：既存ビューの権限はマイグレーションに含まれず、手動SQL（`output/prod_view_definer_setup.sql`、開発は手動作成）で付与されている。そのため今回も手動SQLとする。
- 注意：マイグレーションで作ったビューの定義者は、マイグレーションを実行したDBユーザー（`root`等）になる。`v_ai_shipment`は別途`DEFINER = pm_ai_view_owner`で作り直した経緯がある。`v_ai_product`も、ビュー作成後に下の手順2で定義者を付け替える必要がある。

**実行手順SQL（開発・本番とも。実行はBOSS。本番は事前にバックアップ）**
```sql
-- 1. 定義者の権限を広げる（実行はrootなど管理者で）。2026-10-10 修正：30列（作成日・更新日は含めない）
GRANT SELECT (`id`, `product_code`, `product_name`, `category`, `unit`, `unit_price`, `standard_lt_days`,
  `stock_location`, `processing_area`, `line_id`, `process_id`, `next_process_id`, `management_unit`,
  `is_final_product`, `is_line_final_product`, `is_virtual_set`, `order_lot_min`, `order_lot_multiple`,
  `is_special_management_material`, `specific_gravity`, `size_length`, `size_width`, `size_thickness`,
  `transfer_destination`, `model_name`, `identification_code`, `product_group_id`, `used_container_id`,
  `capacity`, `is_active`)
  ON `pm_db`.`m_product` TO 'pm_ai_view_owner'@'localhost';
-- 2. マイグレーション適用後（開発: python manage.py migrate / 本番: docker exec ... migrate）、定義者を付け替える
-- （DBの選択に依存しないよう、ビューと元テーブルは pm_db で修飾する）
CREATE OR REPLACE DEFINER = `pm_ai_view_owner`@`localhost` SQL SECURITY DEFINER VIEW `pm_db`.`v_ai_product` AS
  SELECT id, product_code, product_name, category, unit, unit_price, standard_lt_days, stock_location,
  processing_area, line_id, process_id, next_process_id, management_unit, is_final_product,
  is_line_final_product, is_virtual_set, order_lot_min, order_lot_multiple, is_special_management_material,
  specific_gravity, size_length, size_width, size_thickness, transfer_destination, model_name,
  identification_code, product_group_id, used_container_id, capacity, is_active
  FROM `pm_db`.`m_product`;
-- 2-2. 【開発DBは32列で作成済みのため追加。2026-10-10】0037のmigrateと上の2の後に、定義者の作成日・更新日の列権限を取り消す
--      （順序注意：ビューが30列になる前に取り消すと、32列のビューが読めなくなる。本番は初回から30列のため、1のGRANTに2列を含めなければ本手順は不要）
--      v_ai_shipment は m_product の id・product_code・product_name だけを使うため、この取り消しの影響を受けない
REVOKE SELECT (`created_at`, `updated_at`) ON `pm_db`.`m_product` FROM 'pm_ai_view_owner'@'localhost';
-- 3. 読み取りユーザーへビューのSELECTのみ付与
--    開発DBの pm_ai_reader は localhost と 10.0.1.36 の2ホストあり、どちらも pm_db 全体への SELECT を持つため、開発では本手順は実質不要
--    （開発では「元テーブルの直接参照が拒否される」確認も成立しない）。本番は SHOW GRANTS FOR で、ホストと権限を確認してから付与する
GRANT SELECT ON `pm_db`.`v_ai_product` TO 'pm_ai_reader'@'<本番のpm_ai_readerのホスト部。SHOW GRANTS FOR で確認>';
-- 4. 確認
SHOW CREATE VIEW `pm_db`.`v_ai_product`;  SHOW GRANTS FOR 'pm_ai_view_owner'@'localhost';
SELECT COUNT(*), SUM(is_active) FROM `pm_db`.`v_ai_product`;  -- 期待値: 2850, 2808
```

**PostgreSQL移行を考慮した構成（BOSS指示 2026-10-10。将来 MySQL→PostgreSQL へ変更し、AI検索もDBへ直接アクセスしない予定）**
- マイグレーション `0034`（32列。のち `0037` で30列に修正）の `CREATE OR REPLACE VIEW v_ai_product AS SELECT <列> FROM m_product` と `DROP VIEW IF EXISTS v_ai_product` は、バッククォート・`DEFINER`・`SQL SECURITY`・DBの修飾を使わない標準SQLで、MySQLでもPostgreSQLでもそのまま通る書き方にした。**PostgreSQLでの実行は未確認**（開発環境にPostgreSQLがない）。
- 定義者・権限は、DBごとに書き方が違うため、マイグレーションに含めず、別の手順SQLにしている。上の手順SQLはMySQL用。PostgreSQLへ移行するときは、次のように書き直す（未実行・未検証。移行時に確認する）。
  - 定義者：PostgreSQLの標準では、ビューの所有者の権限で元テーブルを読む（`security_invoker`を付けない場合）。所有者は専用ロール（例 `pm_ai_view_owner`）にする。`DEFINER`句はない。
  - 列単位の権限：`GRANT SELECT (列, …) ON m_product TO pm_ai_view_owner;`（PostgreSQLも列単位に対応）。
  - 読み取り：`GRANT SELECT ON v_ai_product TO pm_ai_reader;`。元テーブルへの権限は付けない。
  - 確認：`\d+ v_ai_product`、`\dp v_ai_product`、`SELECT count(*), sum(is_active::int) FROM v_ai_product;`。
- PostgreSQLでは、MySQLの`tinyint(1)`が`boolean`になる。`ANALYSIS_COLUMN_TYPES`の型の対応（真偽→BIGINT の0/1）は、移行時に見直す。

**未実装（要確認・BOSS判断待ち）**（2026-10-10 更新: サイクルA・B・Cで解消。§12参照）
- `ANALYSIS_VIEWS`／`ANALYSIS_COLUMN_TYPES`：**サイクルCで登録済み**（`date_field=None`＝全行取得、32列の型は開発DBの`SHOW COLUMNS`に合わせた。2026-10-10に32列から30列へ修正。サイクルA=列型の拡張、サイクルB=date_fieldの任意化）。evaluator未検証。
- `SCREEN_SQL_TABLES`：計画書に許可する画面の指定がないため追加していない（`ai_home`は自動で対象）。マスタ画面（`masters`）・生産・出荷等への許可はBOSS判断（**今も未実装**）。`TERM_COLUMNS`も未変更。
- 列型：開発DBでビュー作成後に`SHOW COLUMNS FROM v_ai_product`を取得し、サイクルCで`ANALYSIS_COLUMN_TYPES`へ反映した（§12）。

## 10. サイクルA: 列型の拡張（2026-10-10。BOSS承認済みの範囲。実装済み・evaluator未検証）

**実装内容**（既存ビュー`v_ai_shipment`・`v_ai_purchase_receipt`の動作は変えない。画面の動作も変わらない）
- `pm_backend/apps/ai/services/analysis_execution_service.py`：`_cell`のDECIMAL分岐を`DECIMAL(p,s)`の一般形へ（`parse_decimal_type`：p 1〜38・s 0〜p、`_decimal_cell`：丸めず、小数桁・整数部の桁の超過・NaN・無限大は`unsupported_value`）。BIGINTは`int`のみ（bool拒否）を維持。
- `analysis-sandbox/job/job_main.py`：`COLUMN_TYPES`の完全一致に加え、`is_allowed_column_type`（`fullmatch`の厳密な正規表現）でDECIMAL(p,s)を許可。`DECIMAL(18,3)`は固定の許可リストから正規表現側へ移したが、結果は従来どおり許可。
- 変更していない：`ANALYSIS_COLUMN_TYPES`、BASE_SQL_SCHEMAとの一致検査、`analysis_guard_runtime.py`（WRAPPER_VERSION不変）。
- 仕様書：`AI分析基盤仕様書.md`の列型（DECIMALの一般化）を追記。

**検証結果**
- `python manage.py test ai.test_analysis_execution`：40件、OK（skipped=2は実launcher用の既存skip）。追加3件（DECIMAL一般形・型名の厳密解釈・BIGINT）を含む。既存の拒否ケース（`test_unsupported_values_are_rejected`）も合格。
- `python -m unittest discover -s analysis-sandbox/tests -p "test_column_types.py"`：2件、OK（job_mainの`validate_header`と`is_allowed_column_type`。Docker・DuckDB不使用）。

**追加修正：DECIMAL(p,s)の先頭ゼロ拒否（2026-10-10。BOSS承認済み）**
- 変更：`analysis_execution_service.py`の`parse_decimal_type`と`job_main.py`の`is_allowed_column_type`の正規表現を、p・sとも「0単独、または先頭が1〜9の1〜2桁」に統一。許可例：DECIMAL(18,3)・(10,0)・(5,0)・(38,2)・(3,3)。拒否例：DECIMAL(18,03)・(01,00)・(018,03)・(00,0)・(5,00)。範囲検査（p 1〜38、s 0〜p）は従来どおり。理由：型名がそのままDuckDBの`CREATE TABLE`に入り、DuckDBが先頭ゼロを受け付けるか未確認のため、最初から通さない。通常の書き方の挙動は変わらない。
- 試験追加：`ai.test_analysis_execution`に1件、`analysis-sandbox/tests/test_column_types.py`に1件。実行結果：`python manage.py test ai.test_analysis_execution`＝41件OK（skipped=2は既存の実launcher用skip）、`test_column_types.py`＝3件OK。
- BOSS承認事項の記録：①`DECIMAL(18,3)`の既存動作の変更（小数4桁以上・整数部15桁超の値を`unsupported_value`で拒否）を承認。②先頭ゼロ拒否を承認。③DuckDBでの取り込み確認（A6）は、作業Cの実データ試験とまとめて行う（未実施）。
- 仕様書：`AI分析基盤仕様書.md`のDECIMAL記述に「先頭ゼロの数字は拒否」を追記。

**未完了**
- A6（DuckDBコンテナ内での`DECIMAL(p,s)`の取り込み確認）：ローカルに`duckdb`が無い（`import duckdb`が失敗）ため**未確認**。コンテナの再ビルド・起動もしていない。
- evaluatorによる検証：未実施。
- サイクルB・C：対象外（未着手）。

**反映状況**：開発・本番とも未反映（コードと試験のみ。コミット・migrate・push・ビルドなし）。

## 11. サイクルB: date_field の任意化（日付なしビューの全行取得。2026-10-10。BOSS承認済みの範囲。実装済み・evaluator未検証）

**実装内容**（既存ビュー`v_ai_shipment`・`v_ai_purchase_receipt`のSQL文字列・パラメータ・検査は変えない。このサイクルでは`v_ai_product`を`ANALYSIS_VIEWS`へ登録しない＝サイクルC）
- `pm_backend/apps/ai/services/analysis_data_service.py`：`build_where(view, date_from, date_to, last_id=None)`を新設（WHERE句と束縛パラメータを返す共通関数）。日付ありは従来と同じ`WHERE `f` >= %s AND `f` <= %s`（+`AND `id` > %s`）、`date_field=None`は期間条件を付けず、`last_id`があるときだけ`WHERE `id` > %s`。`count_target_rows`がこれを使う。`ANALYSIS_VIEWS[view]['date_field']`は`[]`で参照（キーなしはKeyError。`.get()`で補わない）。`validate_datasets`の「日付フィールドを取得列に含める」検査は`date_field`が`None`でないビューにだけ適用。
- `pm_backend/apps/ai/services/analysis_execution_service.py`：`_pages`・`_count`が`build_where`を使う（ページ件数5,000行は変更なし）。
- 変更していない：`analysis_guard_runtime.py`、`ANALYSIS_COLUMN_TYPES`、AIへの指示文、`AIAnalysis.vue`、`TERM_COLUMNS`、`quantity_field`。
- 仕様書：`AI分析基盤仕様書.md`（期間必須規定の取り下げ、日付なしビューの全行取得・COUNT・照合・上限の扱い）。

**検証結果**（偽のDB接続・模擬launcher・SimpleTestCaseのみ。開発DBへの書き込みなし）
- 追加：`pm_backend/apps/ai/test_analysis_dateless_view.py` 10件（B1〜B8。試験側で`ANALYSIS_VIEWS`・`ANALYSIS_COLUMN_TYPES`・`BASE_SQL_SCHEMA`を`patch.dict`し、`date_field=None`の試験用ビュー`v_ai_testmaster`を使用）。`python manage.py test ai.test_analysis_dateless_view`＝10件OK。
- 既存の回帰（個別実行）：`ai.test_analysis_execution` 41件OK（skipped=2は既存の実launcher用）、`ai.test_analysis_planning` 16件OK、`ai.test_analysis_column_guide` 20件OK、`ai.test_analysis_codegen` 74件OK（skipped=2）、`ai.test_analysis_jobs` 25件OK、ほか`ai.test_analysis_*`のSimpleTestCaseのみの各モジュールがOK。
- 未実行：テスト用DBを要する`ai.test_analysis_*`の各モジュール（consult・execution_flow・followup・permissions・reference_*・refinement・run・template_*）は、既存のテスト用DB`test_*`の削除確認で停止し実行できなかった（削除はしていない）。

**未完了**
- evaluatorによる検証：未実施。上記のテスト用DBを要するモジュールの回帰：未確認。
- `v_ai_product`の`ANALYSIS_VIEWS`登録・指示文・画面・`TERM_COLUMNS`：サイクルC（未着手）。

**反映状況**：開発・本番とも未反映（コードと試験のみ。コミット・migrate・push・ビルドなし）。

## 12. サイクルC: v_ai_product の登録と文面（2026-10-10。BOSS承認済みの範囲。実装済み・evaluator未検証）

**実装内容**
- `analysis_data_service.py`：`ANALYSIS_VIEWS`に`v_ai_product`（label=品番マスタ、`date_field=None`、`quantity_field=None`、description）を追加。descriptionは§4.1-1で確認した意味だけを書き、定義のない列は「業務上の意味は未確認」と明記（`unit_price`・`line_id`・`process_id`の空、1行=1品番、`is_active`で絞る、実績ビューのproduct_idとidが結べることを含む）。新設`ai_view_definition(view)`は値が`None`のキーを出さない（日付ありの2ビューは従来と同じ内容）。`count_target_rows`の応答の各ビューに`period_applied`（日付ありtrue・日付なしfalse）を追加（応答の追加のみ）。
- `analysis_execution_service.py`：`ANALYSIS_COLUMN_TYPES`に`v_ai_product`の32列を追加（2026-10-10に30列へ修正）（開発DBの`SHOW COLUMNS`を再取得して照合し、承認済みの対応と食い違いなし）。取得行数上限超過のメッセージを「条件を絞ってください(日付のあるビューは期間も絞れます)」へ（上限値は変更なし）。
- `analysis_planning_service.py`／`analysis_consult_service.py`：AIへ渡す定義を`ai_view_definition`経由に変更。分析案の指示の3か所と承認画面の「条件」（`_conditions_text`。日付ありだけなら従来と同じ文）を日付なしビューに対応（変更前後の全文は`AI分析基盤仕様書.md` §4.7-8に記載）。上限超過の承認時メッセージも同じ趣旨に変更。
- `analysis_codegen_service.py`：日付なしビューを含むときだけ、指示の末尾に`DATELESS_VIEW_RULE`を加える（日付ありだけの指示は1文字も変えない）。`analysis_guard_runtime.py`（WRAPPER_VERSION）は変更なし。
- `AIAnalysis.vue`：件数確認後、`period_applied=false`のビューの行に「期間: 適用しない（全行）」を表示。上限超過のメッセージを「条件（日付のあるビューは期間も）を絞って」へ。
- 変更していない：`SCREEN_SQL_TABLES`、`TERM_COLUMNS`、既存2ビューの`ANALYSIS_VIEWS`・`ANALYSIS_COLUMN_TYPES`。
- 試験：新規`ai.test_analysis_product_view`（11件）。`ai.test_analysis_column_guide`の1件（`process_id`を説明に書かない検査）は、出荷・入荷の説明に限定し、品番マスタは「空の品番がある」と書く承認内容に合わせて更新した。

**検証結果**（開発。読み取りのみ・テスト用DBなし）
- 個別実行：`ai.test_analysis_product_view` 11件OK、`ai.test_analysis_dateless_view` 10件OK、`ai.test_analysis_execution` 41件OK（skipped=2は実launcher用）、`ai.test_analysis_planning` 16件OK、`ai.test_analysis_column_guide` 20件OK、`ai.test_analysis_codegen` 74件OK（skipped=2）、`ai.test_analysis_jobs` 25件OK、`ai.test_analysis_multi_period` 20件OK、`ai.test_analysis_period_warning` 16件OK、`ai.test_analysis_worker_version` 12件OK。フロント`pm-ui/scripts/test-analysis-*.mjs` 7本OK（codegen 67・consult 23・error-banner 6・execution 35・external-confirmation 4・status-monitor 13・templates 53、fail 0）。
- 開発DBの実データ（`pm_ai_reader`接続）：`count_target_rows`相当2,850（`period_applied=false`）、`_count`2,850、`_pages`の全ページ合計2,850（5,000行・1,000行の両方）。全2,850行×32列（2026-10-10に30列へ修正。`created_at`は非公開）で`_cell`が`unsupported_value`を出さない（エラー0件）。NULLは保たれる（`unit_price`2,386・`specific_gravity`1,709・`line_id`1,833・`process_id`2,003・`created_at`0）。`unit_price`=Decimal('42.00')→'42.00'、`specific_gravity`=Decimal('7.8500')→'7.8500'、`created_at`→'2025-12-05 04:16:35.000000'。

**未完了**
- evaluatorによる検証：未実施。実機（AIを使う）の再試験：**未実施**。DuckDBコンテナ内での取り込み確認（A6）：未実施。テスト用DBを要する`ai.test_analysis_*`（consult等）：未実行。
- 画面の「期間: 適用しない（全行）」は件数確認（preview）の後にだけ出る（分析案の段階では`period_applied`が無いため）。承認画面上部の「条件」の文は、分析案作成時から日付なしを反映する。

**反映状況**：開発DBのビュー`v_ai_product`は作成済み（定義者`pm_ai_view_owner`）。コードは未コミット。本番未反映（ビュー作成・権限付与・migrate・push・ビルドなし）。

## 13. 工程マスタのビュー `v_ai_process` の作成前確認（2026-10-10。BOSS承認済み。公開9列。実装は§14）

公開する列は、[AIマスタビュー確認明細](AIマスタビュー確認明細.md) §2 のBOSS判断のとおり。§4.1 の設計原則（1テーブル1ビュー・標準SQL・定義者は `pm_ai_view_owner`・列の説明は仕様書で確認）に従う。

| 確認項目 | 内容 |
|---|---|
| 業務目的 | AIが、工程をコード・名前・ライン・管理単位・稼働率・設備台数で、分析・説明できるようにする。実績ビュー（工程実績・仕損・中断など）の工程IDから、工程の名前や属性を引く |
| 元テーブル | `m_process` の1つだけ。結合なし（行数46） |
| 対象行 | 全行（絞り込みなし）。有効45・無効1。無効の工程は`is_active`で、AIが絞る |
| 数値定義 | なし（マスタ）。件数は行数。`process_code`は46行で重複なし・空なし。**`process_name`は46行中45種類で、同じ名前の工程がある**（「レーザ1」が`0801`と`801`の2つ。`801`は削除予定でBOSS確認済み。時期は未定。AIの説明文には、工程の特定にはコードを使う、とだけ書き、重複の注意は書かない） |
| 公開フィールド（9列） | `id`、`process_code`、`process_name`、`line_id`、`management_unit`、`operating_rate`、`equipment_count`、`two_person_only`、`is_active` |
| 非公開フィールド | `is_outsource`（BOSS判断 2026-10-10。ほとんどが0のため公開しない）、`created_at`、`updated_at`（BOSS判断が未決定のため、非公開として扱う） |
| 個人情報 | なし（個人名・連絡先・認証情報の列を含まない）。列名は、社内AIの列名検査（`SENSITIVE_IDENTIFIER`）に当たらない（実装時に再確認） |
| 検証方法 | ①ビューの行数＝`m_process`の行数（46）②`process_code`の一意性③`is_active`の件数（有効45・無効1）④`pm_ai_reader`でビューが読め、非公開の3列が読めない⑤定義者が`pm_ai_view_owner@localhost`⑥全行×9列が列型の検査（`_cell`）を通る |

### 13.1 列型の対応（`m_process`のSHOW COLUMNSからの導出。ビュー作成後に再確認する）

| 列 | MySQL型 | `ANALYSIS_COLUMN_TYPES` |
|---|---|---|
| `id`、`line_id` | bigint | `BIGINT` |
| `process_code`、`process_name`、`management_unit` | varchar | `VARCHAR` |
| `two_person_only`、`is_active` | tinyint(1) | `BIGINT`（0/1） |
| `equipment_count` | int unsigned | `BIGINT` |
| `operating_rate` | decimal(5,2) | `DECIMAL(18,2)` |

### 13.2 列の意味（仕様書で確認できた範囲。推測は書かない）

| 列 | 仕様書にある意味 | 出典 |
|---|---|---|
| `process_code` | `G`と`PURCHASE`は、実際の工程ではなく、BOM・ルーティングを作るときに、外作（`G`）・購買（`PURCHASE`）を示すための工程（BOSS指示 2026-10-10）。仕様書にも、`G`は外作工程、`PURCHASE`は購入品の工程とある | BOSS指示、仕入れ検収仕様書.md:168、在庫計算仕様書.md:708 |
| `is_outsource`（非公開） | 真なら外作工程として扱う（`process_code='G'`と同じ扱い）。ほとんどが0で、BOSS判断により公開しない | 仕入れ検収仕様書.md:168、購買需要計算仕様書.md:119 |
| `management_unit` | `DAY`=日単位管理（マクロ計画）、`MINUTE`=分単位管理（ミクロ実行）。DBは`MINUTE`が44工程、`DAY`が2工程（うち1つは購買） | モデル定義（`models.py`の選択肢） |
| `equipment_count` | 設備台数。工程負荷は「工程負荷時間÷設備台数」で按分する | 生産計画仕様書.md:739 |
| `line_id` | 工程の所属ライン（工程から見て親にあたるライン）。`m_line.id`と結べる | BOSS指示 2026-10-10 |
| `operating_rate`、`two_person_only` | 項目名のみ（稼働率(%)、2人1設備専用）。業務上の定義の文章は見つからない | 確認明細 §2 |

### 13.3 あわせて変更するもの（案）
1. マイグレーション `0035`：`CREATE OR REPLACE VIEW v_ai_process AS SELECT <9列> FROM m_process`（標準SQLのみ）。ロールバックは`DROP VIEW IF EXISTS v_ai_process`。
2. `migrate`の直後に、`pm_ai_view_owner`へ`m_process`の9列の列単位`SELECT`を付与し（現在、`m_process`への列権限はない）、定義者を`pm_ai_view_owner@localhost`へ付け替える（§4.1の9番。開発DBはBOSSの指示で私が実行、本番は手順SQLをBOSSが実行）。
3. `ANALYSIS_VIEWS`（`date_field=None`・`quantity_field=None`、説明は13.2の範囲）、`ANALYSIS_COLUMN_TYPES`（13.1。ビュー作成後に`SHOW COLUMNS`と照合）、`BASE_SQL_SCHEMA`・`TABLE_NOTES`、仕様書（基盤仕様書・規約辞書・本計画書）を更新する。
4. `SCREEN_SQL_TABLES`と`TERM_COLUMNS`は変更しない。

### 13.4 BOSSに決めてほしいこと
- **既存の`m_process`（元テーブル）の許可との関係**：現在、生産・品質・購買・マスタ画面のチャットSQLは、元テーブル`m_process`を直接参照できる（`sql_queries.py`の`BASE_SQL_SCHEMA`と`SCREEN_SQL_TABLES`）。ビューができた後、元テーブルの許可をビューへ置き換えるかは、既存の動作の変更になる。今回は置き換えず、ビューの追加だけにする案でよいか（置き換えは、全マスタビューが揃ってから、別に判断する）。
- 公開列の9列でよいか（BOSS判断の転記。`is_outsource`は、BOSS指示で非公開に変更）。

## 14. v_ai_process 実装（2026-10-10。BOSS承認済み: §13の公開9列、元テーブルの許可は置き換えずビューの追加のみ。実装済み・evaluator未検証）

**実装内容**
- `pm_backend/apps/ai/migrations/0035_ai_process_view.py` 新規。`CREATE OR REPLACE VIEW v_ai_process`（9列・別名なし・WHEREなし・結合なし・標準SQLのみ）、ロールバックは`DROP VIEW IF EXISTS v_ai_process`。依存は`ai 0034`と`masters 0084`（`two_person_only`の追加。他の8列はそれ以前）。`makemigrations --dry-run`は「No changes detected」。
- `sql_queries.py`：`BASE_SQL_SCHEMA`に`v_ai_process`（9列）、`TABLE_NOTES`に説明を追加（`ai_home`は自動で対象）。既存の`m_process`エントリと`SCREEN_SQL_TABLES`は変更していない。
- `analysis_data_service.py`：`ANALYSIS_VIEWS`に`v_ai_process`（label=工程マスタ、`date_field=None`、`quantity_field=None`、説明は§13.2の範囲のみ）。
- `analysis_execution_service.py`：`ANALYSIS_COLUMN_TYPES`に9列（§13.1）。
- 仕様書：`AI分析基盤仕様書.md`（公開ビュー一覧・型の対応）、`AI運用規約・AI用DB辞書.md`（§6.5-5を追加。既存の「品番・顧客コード・納入先コードの表記」は§6.5-6へ番号を繰り下げ）。

**検証結果**（開発。読み取りのみ・テスト用DBなし）
- 新規`ai.test_analysis_process_view` 9件を含め、`ai.test_analysis_process_view`・`product_view`・`dateless_view`・`execution`・`planning`・`column_guide`・`codegen`・`jobs`・`multi_period`・`period_warning`・`worker_version`の1コマンド実行で254件OK（再検証の時点では、別セッションが追加した試験を含めて265件OK。skipped=4は既存の実launcher用等）。フロント`pm-ui/scripts/test-analysis-*.mjs` 7本OK（codegen 68・consult 23・error-banner 6・execution 35・external-confirmation 4・status-monitor 13・templates 53、fail 0）。
- 開発DBの実データ（`pm_ai_reader`接続、`SELECT <9列> FROM m_process`）：46行・有効45・`process_code`の重複なし。全46行×9列が`_cell`を通る（エラー0件）。`m_process`のSHOW COLUMNS（bigint・varchar・tinyint(1)・int unsigned・decimal(5,2)）は§13.1の対応と一致。

**未完了**
- 実装時点は、開発DBにビュー`v_ai_process`が未作成だった。**その後、開発DBで実施済み**（BOSS承認 2026-10-10）：`migrate ai 0035`でビュー作成、`pm_ai_view_owner`へ`m_process`の9列の列権限を付与、定義者を`pm_ai_view_owner@localhost`へ付け替え（§4.1の9番）。確認結果：`SHOW COLUMNS FROM v_ai_process`は9列で、型は`ANALYSIS_COLUMN_TYPES`の対応（bigint・varchar・decimal(5,2)・int unsigned・tinyint(1)）と一致。`pm_ai_reader`の接続で、件数46・有効45・`process_code`の種類46。`is_outsource`・`created_at`・`updated_at`は読めない（列がない）。4つの`v_ai_`ビューの定義者は、すべて`pm_ai_view_owner@localhost`。
- evaluatorによる検証：未実施。実機（AIを使う）の再試験：未実施。テスト用DBを要する`ai.test_analysis_*`：未実行。

**反映状況**：開発DBにビュー作成済み・定義者付け替え済み（2026-10-10）。コミット・本番未反映。本番は、`migrate 0035`のあとに、権限付与と定義者の付け替えをBOSSが実行する（§4.1の9番）。

### 14.1 本番・開発の手順SQL（v_ai_process。実行はBOSS。本番は事前にバックアップ。Codexレビュー指摘への対応。2026-10-10）
```sql
-- 1. 定義者の権限を9列へ広げる（rootなど管理者で）
GRANT SELECT (`id`, `process_code`, `process_name`, `line_id`, `management_unit`, `operating_rate`,
  `equipment_count`, `two_person_only`, `is_active`)
  ON `pm_db`.`m_process` TO 'pm_ai_view_owner'@'localhost';
-- 2. マイグレーション適用後（開発: python manage.py migrate / 本番: docker exec ... migrate）、定義者を付け替える
CREATE OR REPLACE DEFINER = `pm_ai_view_owner`@`localhost` SQL SECURITY DEFINER VIEW `pm_db`.`v_ai_process` AS
  SELECT `id`, `process_code`, `process_name`, `line_id`, `management_unit`, `operating_rate`,
  `equipment_count`, `two_person_only`, `is_active`
  FROM `pm_db`.`m_process`;
-- 3. 読み取りユーザーへビューのSELECTのみ付与（開発のpm_ai_readerはDB全体のSELECTを持つため、実質不要。本番はSHOW GRANTSで確認してから）
GRANT SELECT ON `pm_db`.`v_ai_process` TO 'pm_ai_reader'@'<本番のpm_ai_readerのホスト部。SHOW GRANTS FOR で確認>';
-- 4. 確認
SELECT TABLE_NAME, DEFINER, SECURITY_TYPE FROM information_schema.VIEWS WHERE TABLE_SCHEMA = 'pm_db' AND TABLE_NAME = 'v_ai_process';
SELECT COUNT(*), SUM(is_active), COUNT(DISTINCT process_code) FROM `pm_db`.`v_ai_process`;  -- 開発の期待値: 46, 45, 46
SHOW GRANTS FOR 'pm_ai_view_owner'@'localhost';
```

## 15. ラインマスタのビュー `v_ai_line` の作成前確認（2026-10-10。BOSS承認済み。公開6列。実装は§16）

公開する列は、[AIマスタビュー確認明細](AIマスタビュー確認明細.md) §3 のBOSS判断のとおり。§4.1 の設計原則（1テーブル1ビュー・標準SQL・定義者は `pm_ai_view_owner`・列の説明は仕様書で確認）に従う。

| 確認項目 | 内容 |
|---|---|
| 業務目的 | AIが、ラインをコード・名前・種別・カレンダで、分析・説明できるようにする。実績・計画・工程・BOMなどのビューのライン（`line_id`）から、ラインの名前や種別を引く |
| 元テーブル | `m_line` の1つだけ。結合なし（行数57） |
| 対象行 | 全行（絞り込みなし）。有効56・無効1。購買ライン（`PURCHASE`）を含む。無効のラインは`is_active`で、AIが絞る |
| 数値定義 | なし（マスタ）。件数は行数。`line_code`は57行で重複なし・空なし。`line_name`も57行で重複なし |
| 公開フィールド（6列） | `id`、`line_code`、`line_name`、`calendar_id`、`line_type`、`is_active` |
| 非公開フィールド | `lead_time_days`（BOSS判断 2026-10-10。現在は使っていないため）、`use_direct_process`（同。現在は実質使っていないため）、`created_at`、`updated_at`（BOSS判断が未決定のため、非公開として扱う） |
| 個人情報 | なし。ただし、購買ラインの`line_name`は**仕入先の会社名**（例: エトー株式会社）で、`line_code`は仕入先コード。AIは、仕入先名を、コードの置き換えなしで読める（仕入先名は会社名で個人情報ではない。外部AIへ送る目的文の置換は従来どおり） |
| 検証方法 | ①ビューの行数＝`m_line`の行数（57）②`line_code`の一意性③`is_active`の件数（有効56・無効1）④`pm_ai_reader`でビューが読め、非公開の4列が読めない⑤定義者が`pm_ai_view_owner@localhost`⑥全行×6列が列型の検査（`_cell`）を通る |

### 15.1 実データ（開発DB）
- ライン種別（`line_type`）：`PROD`（社内ライン）26（有効26）、`PURCHASE`（購買ライン）29（有効29）、`OUTSOURCE`（外作）1（有効0）、`OTHER`1（有効1）。
- `calendar_id`が空のラインが38。`lead_time_days`は空なし（0〜2）。`use_direct_process`が真のラインは1（板金スポットライン）。
- `line_code`は、先頭がゼロのものが27（購買ラインの仕入先コード。例 `000044`）、英字で始まるものが30。**文字列のまま扱う。**

### 15.2 列型の対応（`m_line`のSHOW COLUMNSからの導出。ビュー作成後に再確認する）
| 列 | MySQL型 | `ANALYSIS_COLUMN_TYPES` |
|---|---|---|
| `id`、`calendar_id` | bigint | `BIGINT` |
| `line_code`、`line_name`、`line_type` | varchar | `VARCHAR` |
| `is_active` | tinyint(1) | `BIGINT`（0/1） |

### 15.3 列の意味（仕様書で確認できた範囲。推測は書かない）
| 列 | 仕様書にある意味 | 出典 |
|---|---|---|
| `line_type` | 値は `PROD`・`PURCHASE`・`OUTSOURCE`・`OTHER`。意味は、§15.5のBOSSの説明のとおり（`PROD`は社内ライン、`PURCHASE`は外作先・購入先の購買ライン、`OUTSOURCE`は外作ライン（使っていない・削除予定）、`OTHER`はクボタ納期調整） | BOSS説明、ER_diagram_v3.md:23、単独計画仕様書.md:24、仕入れ検収仕様書.md:76、仕入れ先カレンダ仕様書.md:18 |
| `line_code` | 購買ラインでは仕入先コード | 仕入れ先カレンダ仕様書.md:18、仕入れ検収仕様書.md:76 |
| `calendar_id` | ラインの勤務カレンダ（購買ラインでは、仕入先のカレンダの割当先）。`m_calendar_day`の`calendar_id`と結べる | モデルの項目名、仕入れ先カレンダ仕様書.md:28 |
| `is_active` | 有効（1）／無効（0）。**ER図は「購買ラインは意図的に0」と書くが、開発DBでは購買ライン29がすべて1。仕様書と実データが食い違う（下記）** | ER_diagram_v3.md:9-11、DB実データ |
| `lead_time_days`、`use_direct_process`（非公開） | 項目名のみ（リードタイム(日)、工程直接展開）。BOSS判断で非公開にした。意味と使われ方は§15.5 | 確認明細 §3 |

### 15.4 BOSSに決めてほしいこと
- ~~公開列の8列でよいか~~ → **決定済み（2026-10-10）**：6列（`lead_time_days`・`use_direct_process`は、BOSS判断で非公開）。
- ~~`is_active`の説明~~ → **決定済み（承認）**：ER図は購買ラインを「意図的に`is_active=0`」とするが、開発DBでは購買ライン29がすべて有効（1）。AIの説明文には、「`is_active`は有効(1)・無効(0)」とだけ書き、購買ラインの扱いは書かない案でよいか。
- ~~元テーブル`m_line`の許可~~ → **決定済み（承認）**：置き換えず、ビューの追加だけにする（工程のときと同じ）。
- ~~`lead_time_days`・`use_direct_process`の意味~~ → **決定済み**：BOSSの説明とコード調査を§15.5に記録。2列とも非公開。

### 15.5 列の意味の追記（BOSS説明・コード調査。2026-10-10）
| 列 | 意味 | 出典 |
|---|---|---|
| `line_type` | **BOSSの説明（2026-10-10）**：`PROD`=社内ライン（社内だけに絞るときに使う）。`PURCHASE`=仕入先の購買ライン（外作先・購入先のライン。社内ライン以外のライン。コード=仕入先コード、名前=仕入先の会社名）。`OUTSOURCE`=外作ライン（ID14 `GAISAKU`。**現在は使っていない。削除予定**）。`OTHER`=クボタ納期調整（ID103 `KBT_DUE_ADJ`。意味の文章は未確認）。コードの調査：`OUTSOURCE`は、購買ラインの品を外作ライン・外作工程へ切り替える／戻す管理コマンドがあり、受注展開・バックログ・生産実績の整合チェックで`PROD`と並んで対象 | BOSS説明、`convert_purchase_to_gaisaku.py`・`revert_gaisaku_line_to_supplier.py`、生産実績整合チェック仕様書.md:18 |
| `lead_time_days` | リードタイム(日)。**最初は使ったが、後では使わなくなった（BOSS）**。主なリードタイムはルーティング工程側。コードには、工程側が空のときの代替などの参照が残る（`lead_time_utils.py`、`bom_service.py:87-92`、`inventory_calculator.py:404`）。値は、0日が50ライン、1日が6、2日が1 | BOSS説明、コード調査 |
| `use_direct_process` | 自動計画の展開で、ルーティングを使わず、指定の工程に直接書き込む（スポット系ライン向け）。BOMの員数の掛け算も行わない。真なのは、ID10「板金スポットライン」の1つだけ。**BOSSは、板金スポットラインのExcel導入（計画入力画面のスポット→Excel→forup取込）に使う、と推測。コード調査では、Excel取込の処理に、このフラグの参照は見つからなかった（参照は、自動計画の生成コマンドだけ）** | モデルの説明文、`generate_production_plan.py:435`、`auto_plan_expansion.py:28` |

**BOSS判断（2026-10-10。判断画面で変更）**：`lead_time_days`（現在使っていない）と`use_direct_process`（自動計画の展開用。板金スポットラインの自動計画は無効で、実質使っていない）は、**非公開**にした。公開は6列。`use_direct_process`の使用箇所は、リポジトリ全体の検索で、自動計画の生成コマンド（`generate_production_plan.py:435`）の1か所だけ。板金スポットラインの自動計画の設定（ID10）は無効で、最後の実行は2026-03-01。

### 15.6 BOSS指摘への調査結果（2026-10-10。ライン編集画面）
- **`line_type='PURCHASE'`**：仕入先の購買ライン。外作先と購入先を絞るときに使う（BOSS）。開発DBでは、購買ライン29の`line_code`が、すべて仕入先コードと一致し、仕入先29（`purchase`＝購入先17、`outsource`＝外作先9、`both`＝両方3）と同数。
- **所属グループ**：`m_line`に列はない。別テーブル `accounts_unit_line_mapping`（`unit_id`＝グループ、`line_id`、`sort_order`、`is_default`、作成・更新日時）に持つ。グループは`accounts_department`の`level='unit'`の行（フロア・タンク・第一工場・第二工場・板金・調達・出荷の6つ）。28行、21ライン。**36ラインは、グループ未割当**。割当があるのは、すべて`PROD`のライン。→ 1テーブル1ビューの原則に従い、**別のビュー（案：`v_ai_unit_line`）にする**。
- **このラインを使用する工程**：画面は、ルーティングではなく**工程マスタの`line_id`**から集計している（`LineMaster.vue:210`）。`v_ai_process`の`line_id`で、AIも同じ関係を引ける。工程を持つラインは27。ルーティング工程が使うラインは53（別のビュー）。

## 16. v_ai_line 実装（2026-10-10。BOSS承認済み: §15の公開6列、元テーブルの許可は置き換えずビューの追加のみ。実装済み・evaluator未検証）

**実装内容**
- `pm_backend/apps/ai/migrations/0036_ai_line_view.py` 新規。`CREATE OR REPLACE VIEW v_ai_line`（6列・別名なし・WHEREなし・結合なし・標準SQLのみ）、ロールバックは`DROP VIEW IF EXISTS v_ai_line`。依存は`ai 0035`と`masters 0023`（`line_type`の追加。`calendar_id`は0015、他の4列は0001）。`makemigrations --dry-run`は「No changes detected」。
- `sql_queries.py`：`BASE_SQL_SCHEMA`に`v_ai_line`（6列）、`TABLE_NOTES`に説明を追加（`ai_home`などは自動で対象）。既存の`m_line`エントリと`SCREEN_SQL_TABLES`は変更していない。
- `analysis_data_service.py`：`ANALYSIS_VIEWS`に`v_ai_line`（label=ラインマスタ、`date_field=None`、`quantity_field=None`、説明は§15.3・§15.5の範囲のみ。`lead_time_days`・`use_direct_process`・`created_at`・`updated_at`と、購買ラインの`is_active`の扱いは書かない）。
- `analysis_execution_service.py`：`ANALYSIS_COLUMN_TYPES`に6列（§15.2）。
- 試験：`apps/ai/test_analysis_line_view.py` 新規。既存の`test_analysis_column_guide.py`の1検査を更新（下記）。
- 仕様書：`AI分析基盤仕様書.md`（公開ビュー一覧・型の対応）、`AI運用規約・AI用DB辞書.md`（§6.5-6を追加。既存の「品番・顧客コード・納入先コードの表記」は§6.5-7へ繰り下げ。他の文書・コードに§6.5-6への参照はなかった）。

**既存試験の更新（承認範囲の反映。検査は弱めていない）**
- `test_analysis_column_guide.py` の `test_no_real_data_note_and_no_unconfirmed_meaning`：全ビューの説明に「クボタ」が入らないことの検査が、`line_type`の値の名称「OTHER=クボタ納期調整」（BOSS承認）で失敗したため、この語句だけを除いた文字列で「クボタ」の不在を検査するように変更。これ以外の「クボタ」は従来どおり不可。

**検証結果**（開発。読み取りのみ・テスト用DBなし）
- 新規`ai.test_analysis_line_view` 9件を含め、`ai.test_analysis_line_view`・`process_view`・`product_view`・`dateless_view`・`execution`・`planning`・`column_guide`・`codegen`・`jobs`・`multi_period`・`period_warning`・`worker_version`の1コマンド実行で263件OK（skipped=4）。フロント`pm-ui/scripts/test-analysis-*.mjs` 7本OK（codegen 68・consult 23・error-banner 6・execution 35・external-confirmation 4・status-monitor 13・templates 53、fail 0）。
- 開発DBの実データ（`AI_DB_ALIAS`接続、`SELECT <6列> FROM m_line`）：57行・有効56・`line_code`の重複なし・`calendar_id`が空38。全57行×6列が`_cell`を通る（エラー0件）。`m_line`のSHOW COLUMNS（bigint・varchar(20/50/20)・tinyint(1)）は§15.2の対応と一致。

**未完了**
- 実装時点は、開発DBにビュー`v_ai_line`が未作成だった。**その後、開発DBで実施済み**（BOSS承認 2026-10-10）：`migrate ai 0036`でビュー作成、`pm_ai_view_owner`へ`m_line`の6列の列権限を付与、定義者を`pm_ai_view_owner@localhost`へ付け替え（§4.1の9番）。確認結果：`SHOW COLUMNS FROM v_ai_line`は6列で、型は`ANALYSIS_COLUMN_TYPES`の対応（bigint・varchar・tinyint(1)）と一致。`pm_ai_reader`の接続で、件数57・有効56・`line_code`の種類57。`lead_time_days`・`use_direct_process`・`created_at`・`updated_at`は読めない（列がない）。全57行×6列が列型の検査を通る（エラー0）。5つの`v_ai_`ビューの定義者は、すべて`pm_ai_view_owner@localhost`。
- evaluatorによる検証：未実施。実機（AIを使う）の再試験：未実施。テスト用DBを要する`ai.test_analysis_*`：未実行。

**反映状況**：開発DBにビュー作成済み・定義者付け替え済み（2026-10-10）。本番未反映。本番は、`migrate 0036`のあとに、権限付与と定義者の付け替えをBOSSが実行する（§4.1の9番）。

### 16.1 本番・開発の手順SQL（v_ai_line。実行はBOSS。本番は事前にバックアップ。Codexレビュー指摘への対応。2026-10-10）
```sql
-- 1. 定義者の権限を6列へ広げる（rootなど管理者で）
GRANT SELECT (`id`, `line_code`, `line_name`, `calendar_id`, `line_type`, `is_active`)
  ON `pm_db`.`m_line` TO 'pm_ai_view_owner'@'localhost';
-- 2. マイグレーション適用後、定義者を付け替える
CREATE OR REPLACE DEFINER = `pm_ai_view_owner`@`localhost` SQL SECURITY DEFINER VIEW `pm_db`.`v_ai_line` AS
  SELECT `id`, `line_code`, `line_name`, `calendar_id`, `line_type`, `is_active`
  FROM `pm_db`.`m_line`;
-- 3. 読み取りユーザーへビューのSELECTのみ付与（開発のpm_ai_readerはDB全体のSELECTを持つため、実質不要。本番はSHOW GRANTSで確認してから）
GRANT SELECT ON `pm_db`.`v_ai_line` TO 'pm_ai_reader'@'<本番のpm_ai_readerのホスト部。SHOW GRANTS FOR で確認>';
-- 4. 確認
SELECT TABLE_NAME, DEFINER, SECURITY_TYPE FROM information_schema.VIEWS WHERE TABLE_SCHEMA = 'pm_db' AND TABLE_NAME = 'v_ai_line';
SELECT COUNT(*), SUM(is_active), COUNT(DISTINCT line_code) FROM `pm_db`.`v_ai_line`;  -- 開発の期待値: 57, 56, 57
SHOW GRANTS FOR 'pm_ai_view_owner'@'localhost';
```

## 17. 仕入先マスタのビュー `v_ai_supplier` の作成前確認（2026-10-10。BOSS承認済み。実装は§19。§8を置き換える）

公開する列は、[AIマスタビュー確認明細](AIマスタビュー確認明細.md) §4 のBOSS判断のとおり。§4.1 の設計原則（1テーブル1ビュー・標準SQL・定義者は `pm_ai_view_owner`・列の説明は仕様書で確認）に従う。§8（2026-10-08）の草案は、「入荷ビューに仕入先の列を足さず、AIにビュー同士を結合させる」という方針で書かれており、今回の原則（結合は、マスタの属性を付けるときだけ可。実績同士は不可）と矛盾しない範囲で引き継ぐ。

| 確認項目 | 内容 |
|---|---|
| 業務目的 | AIが、仕入先をコード・名前・区分・カレンダで、分析・説明できるようにする。入荷実績ビュー（`v_ai_purchase_receipt`）の`supplier_id`から、仕入先のコード・名前を引く（仕入先ごとの入荷の集計の表示に、内部のIDを出さない） |
| 元テーブル | `m_supplier` の1つだけ。結合なし（行数29） |
| 対象行 | 全行（絞り込みなし）。`is_active`の列はない |
| 数値定義 | なし（マスタ）。件数は行数。`supplier_code`は29行で重複なし。`supplier_name`も29種類 |
| 公開フィールド（5列） | `id`、`supplier_code`、`supplier_name`、`supplier_type`、`calendar_id` |
| 非公開フィールド | `contact_person`（担当者名）、`phone_number`（電話番号）、`order_email`（送信メールアドレス）。個人名・連絡先のため |
| 個人情報 | 仕入先名は会社名（個人名ではない）。個人名・電話・メールの3列は、ビューに含めない。外部AIへ送る目的文の、名称→コード置換は、従来どおり（運用規約 §4.1-3） |
| 検証方法 | ①ビューの行数＝`m_supplier`の行数（29）②`supplier_code`の一意性③区分の件数（購入17・外作9・両方3）④`pm_ai_reader`でビューが読め、非公開の3列が読めない⑤定義者が`pm_ai_view_owner@localhost`⑥全行×5列が列型の検査（`_cell`）を通る⑦入荷実績ビューの仕入先別の集計（9月: 仕入先16=20,259・仕入先8=11,270。§8の記録）を、コード・名前つきで照合 |

### 17.1 実データ（開発DB）
- 29行。区分は、購入（`purchase`）17、外作（`outsource`）9、両方（`both`）3。
- `calendar_id`が空の仕入先が28（仕入先専用カレンダがあるのは1つ）。
- `supplier_code`は、先頭がゼロのものが27、英字で始まるものが2（例 `G00001`）。最大6桁。**文字列のまま扱う。**
- 購買ライン（`line_type='PURCHASE'`）29の`line_code`が、すべて仕入先コードと一致する（ラインビュー §15.6）。

### 17.2 列型の対応（`m_supplier`のSHOW COLUMNSからの導出。ビュー作成後に再確認する）
| 列 | MySQL型 | `ANALYSIS_COLUMN_TYPES` |
|---|---|---|
| `id`、`calendar_id` | bigint | `BIGINT` |
| `supplier_code`、`supplier_name`、`supplier_type` | varchar | `VARCHAR` |

### 17.3 列の意味（仕様書で確認できた範囲。推測は書かない）
| 列 | 意味 | 出典 |
|---|---|---|
| `supplier_type` | 値は `purchase`=購入、`outsource`=外作、`both`=両方。購入先・外作先を分けるときに使う（購買ラインの種別と同じ、BOSS説明） | モデルの選択肢（`models.py`）、BOSS説明（ライン§15.5） |
| `supplier_code` | 仕入先コード。購買ラインの`line_code`と同じ。先頭ゼロを含む文字列 | 仕入れ先カレンダ仕様書.md:18、仕入れ検収仕様書.md:76 |
| `supplier_name` | 仕入先名（会社名） | 項目名 |
| `calendar_id` | 仕入先専用カレンダー（稼働カレンダの`calendar_id`と結べる。空の仕入先が多い） | モデルの項目名、自動発注提案仕様書.md:39、AIマスタビュー確認明細.md（BOSS判断） |

### 17.4 あわせて変更するもの（実施内容は§19）
1. マイグレーション `0038`：`CREATE OR REPLACE VIEW v_ai_supplier AS SELECT <5列> FROM m_supplier`（標準SQLのみ）。ロールバックは`DROP VIEW IF EXISTS v_ai_supplier`。
2. `migrate`の直後に、`pm_ai_view_owner`へ`m_supplier`の5列の列単位`SELECT`を付与し（現在、`m_supplier`への列権限はない）、定義者を`pm_ai_view_owner@localhost`へ付け替える（§4.1の9番）。
3. `ANALYSIS_VIEWS`・`ANALYSIS_COLUMN_TYPES`・`BASE_SQL_SCHEMA`・`TABLE_NOTES`・仕様書を更新する。`v_ai_purchase_receipt`の列は変えない（既存ビューの定義を変えると、保存済みテンプレートが再利用できなくなる）。
4. `SCREEN_SQL_TABLES`・`TERM_COLUMNS`・AIへの指示文は変更しない。元テーブル`m_supplier`の許可（購買画面）は、置き換えず、ビューの追加だけにする。

### 17.5 BOSSに決めてほしいこと
- ~~公開列の5列でよいか~~ → **決定済み（承認 2026-10-10）**：5列（BOSS判断の転記どおり）。
- ~~元テーブル`m_supplier`の許可~~ → **決定済み（承認）**：置き換えず、ビューの追加だけにする。
- ~~§8の古い草案を、この§17に置き換えてよいか~~ → **決定済み（承認）**：§17に置き換える。

### 17.6 仕入先とラインの関係（BOSS指摘への調査。2026-10-10。開発DB・読み取りのみ）
- **仕入先と購買ラインは、1対1。つなぐ列は、ラインの`line_code`と仕入先の`supplier_code`（文字列の一致）。** 外部キー（ID）では結ばれていない。購買ライン（`line_type='PURCHASE'`）29と、仕入先29が、すべて、コードで一致する（仕入れ先カレンダ仕様書.md:18、仕入れ検収仕様書.md:76）。
- **LineBacklog（`line_backlog`）**：`line_id`は`m_line`のID。仕入先の列はない。購買ラインの行は148,445行（28ライン）で、すべて、`line_code`が仕入先コードと一致する。社内ライン（`PROD`）は350,870行（25ライン）。→ 仕入先を知るには、`line_id`→ラインの`line_code`→仕入先の`supplier_code`。
- **工程実績（`t_process_realtime_record`）**：`line_id`の**列はない**。仕入実績（`record_type='PURCHASE'`）は、`event_data`（JSON）の中に`line_id`と`supplier_id`を持つ。2,872行すべてが`supplier_id`を持ち、2,831行が`line_id`を持つ。この2,831行は、`line_id`が購買ラインで、そのラインの`line_code`が、`supplier_id`の仕入先コードと一致する（2,831行すべて）。`line_id`を持たない41行は、工程コードが`PURCHASE`（購入）の行。工程コードが`G`（外作）の行は、2,831行。→ 入荷実績ビュー（`v_ai_purchase_receipt`）は、`supplier_id`と`line_id`の両方を、列として持つ。
- **工程マスタの`line_id`**：`G`・`PURCHASE`の工程は、ラインを持たない（`m_process.line_id`は空）。仕入先の区別は、工程ではなく、ラインで行う（仕入実績record_type分離仕様書.md:25）。
- **ルーティング工程**：ラインの種別は、社内4,707、購買2,970、外作1。`supplier_id`を持つのは534行。
- **AIへの説明**：`v_ai_line`と`v_ai_supplier`の説明に、「購買ラインの`line_code`＝仕入先の`supplier_code`（同じ文字列で結べる。先頭ゼロを含む）」を書く。

## 18. 日付なしビューの指示文の見直し（2026-10-10。BOSS承認済み。Codex第2回レビュー指摘1への対応。実装済み・evaluator未検証）

**背景**：日付なしビュー（`v_ai_product`・`v_ai_process`・`v_ai_line`）に対し、AIが`created_at BETWEEN {{period_from}} AND {{period_to}}`のような日付の絞り込みを付けても、生成物の検査では拒否できない。BOSS判断：日付なしビューの日付の列で絞る分析は正しい分析であり、検査は追加しない。代わりに指示文を、日付の列で絞る分析を禁止しない形に直し、「必ず`parameters_unused`で拒否される」という説明を訂正する。

**実装内容**
- `pm_backend/apps/ai/services/analysis_codegen_service.py`：`DATELESS_VIEW_RULE`のみ書き換え（`SYSTEM_PROMPT`本体は変更なし。日付ありだけのsystemは変更前と同一）。
  - 変更前：「日付の列を持たない承認ビュー(datasetsのdescriptionに「期間では絞らず全行が対象」とあるビュー)は、期間で絞らず全行を使う(そのビューに期間の条件や日付の条件を付けない)。期間の変数 period_from・period_to は、日付のあるビューの条件にだけ使う。」
  - 変更後：「日付の列を持たない承認ビュー(datasetsのdescriptionに「期間では絞らず全行が対象」とあるビュー)は、システムの期間では絞られず、全行が取り込まれる。分析の中で、目的に応じて、そのビューの日付の列(descriptionに列があるもの)で絞るのは構わない。システムの期間の変数 period_from・period_to は、日付のあるビューの期間条件に使う。目的が日付での絞り込みを求めていない場合は、日付の条件を付けない。」
- 検査（`validate_generated`・`_apply_parameters`）、`analysis_guard_runtime.py`、既存ビューの登録は変更なし。上限値・フォールバックの新設なし。
- 仕様書：`AI分析基盤仕様書.md`（§4.7-8の指示文の記録、日付なしビューの日付の列での絞り込みを追記）、`Codexレビュー依頼_AI用ビュー.md`（指摘1の対応欄と確認項目7を更新）。

**検証結果**（DBを作らない試験のみ）：`ai.test_analysis_*`の12モジュールを1コマンドで263件OK（skipped=4。その後、品番の30列化と別セッションの追加を含めて265件OK）。`pm-ui/scripts/test-analysis-*.mjs` 7本 fail 0。既存の試験の更新は不要（`test_analysis_product_view.py`は定数参照で比較しており、日付あり単独のsystemがSYSTEM_PROMPTと一致する検査もそのまま合格）。

**未完了**：evaluatorによる検証、実機のAI再試験（日付なしビューの日付の列で絞る目的・絞らない目的の両方）。

**反映状況**：コード変更のみ。コミット・本番未反映。

## 19. v_ai_supplier 実装（2026-10-10。BOSS承認済み: §17の公開5列、元テーブルの許可は置き換えずビューの追加のみ。実装済み・evaluator未検証）

**実装内容**
- `pm_backend/apps/ai/migrations/0038_ai_supplier_view.py` 新規。`CREATE OR REPLACE VIEW v_ai_supplier`（5列・別名なし・WHEREなし・結合なし・標準SQLのみ）、ロールバックは`DROP VIEW IF EXISTS v_ai_supplier`。依存は`ai 0037`と`masters 0059`（`supplier_type`の追加。`calendar_id`は0032、他の3列は0001）。`makemigrations --dry-run`は「No changes detected」。
- `sql_queries.py`：`BASE_SQL_SCHEMA`に`v_ai_supplier`（5列）、`TABLE_NOTES`に説明を追加。既存の`m_supplier`エントリと`SCREEN_SQL_TABLES`は変更していない。
- `analysis_data_service.py`：`ANALYSIS_VIEWS`に`v_ai_supplier`（label=仕入先マスタ、`date_field=None`、`quantity_field=None`、説明は§17.3の範囲のみ。`contact_person`・`phone_number`・`order_email`は書かない）。
- `analysis_execution_service.py`：`ANALYSIS_COLUMN_TYPES`に5列（§17.2）。
- 試験：`apps/ai/test_analysis_supplier_view.py` 新規（10件）。既存の試験の更新は不要（既存ビューの出力は変わらず、既存の固定ハッシュはすべて同じ値のまま合格）。
- 仕様書：`AI分析基盤仕様書.md`（公開ビュー一覧・型の対応）、`AI運用規約・AI用DB辞書.md`（§6.5-7を追加。既存の「品番・顧客コード・納入先コードの表記」は§6.5-8へ繰り下げ（その時点の番号。得意先マスタ（§22）の追加で、さらに§6.5-9へ繰り下げた）。他の文書・コードに§6.5-7・§6.5-8への参照はなかった）。
- 既存ビュー5つ（出荷・入荷・品番・工程・ライン）の定義（説明・列）のJSONのSHA-256（新規試験の固定値）：`aaed5cd71d844171d20fc26e92ab5a257bec3b4929b7c54e88781206a4abe454`。v_ai_supplier の追加前後で同一（追加は、既存エントリを変えない追記のみ）。既存4ビューの値は`12dd1770…`、既存3ビューの値は`4d111066…`で、既存の試験の固定値と一致した。

**検証結果**（開発。読み取りのみ・テスト用DBなし）
- 新規`ai.test_analysis_supplier_view` 10件を含め、`ai.test_analysis_supplier_view`・`line_view`・`process_view`・`product_view`・`dateless_view`・`execution`・`planning`・`column_guide`・`codegen`・`jobs`・`multi_period`・`period_warning`・`worker_version`の1コマンド実行で275件OK（skipped=4）。フロント`pm-ui/scripts/test-analysis-*.mjs` 7本OK（codegen 68・consult 23・error-banner 6・execution 35・external-confirmation 4・status-monitor 13・templates 53、fail 0）。
- 開発DBの実データ（`AI_DB_ALIAS`接続、`SELECT <5列> FROM m_supplier`）：29行・`supplier_code`の重複なし（29種類）・区分は購入17・外作9・両方3・`calendar_id`が空28。全29行×5列が`_cell`を通る（エラー0件）。`m_supplier`のSHOW COLUMNS（bigint・varchar(20/100/20)・bigint）は§17.2の対応と一致。入荷実績ビューの`supplier_id`は2,872行すべて値があり、`m_supplier.id`に存在しない行は0件。

**未完了**
- 実装時点は、開発DBにビュー`v_ai_supplier`が未作成だった。**その後、開発DBで実施済み**（BOSS承認 2026-10-10）：`migrate ai 0038`（21:06に適用済み。実行者は記録上不明）、`setup_ai_views --apply`（定義者を`pm_ai_view_owner@localhost`へ付け替え、`m_supplier`の5列の列権限を付与。コマンドの最初の実機実行）。確認結果：`SHOW COLUMNS FROM v_ai_supplier`は5列で、型は`ANALYSIS_COLUMN_TYPES`の対応（bigint・varchar）と一致。`pm_ai_reader`の接続で、29件・コード29種類・区分は購入17・外作9・両方3。`contact_person`・`phone_number`・`order_email`は読めない（列がない）。全29行×5列が列型の検査を通る（エラー0）。入荷ビューの仕入先IDで、仕入先ビューにない行は0件。購買ライン29が、仕入先コードですべて結合できる。6つの`v_ai_`ビューの定義者は、すべて`pm_ai_view_owner@localhost`。`setup_ai_views --check`は要対応0件。
- evaluatorによる検証：未実施。実機（AIを使う）の再試験：未実施。テスト用DBを要する`ai.test_analysis_*`：未実行。

**反映状況**：開発DBにビュー作成済み・定義者付け替え済み（2026-10-10）。本番未反映。本番は、`migrate 0038`のあとに、`setup_ai_views --apply`（管理者で実行）で、権限付与と定義者の付け替えをBOSSが実行する（§20）。

### 19.1 本番・開発の手順SQL（v_ai_supplier。実行はBOSS。本番は事前にバックアップ）
```sql
-- 1. 定義者の権限を5列へ広げる（rootなど管理者で。現在、m_supplierへの列権限はない。担当者名・電話番号・メールアドレスの列は付与しない）
GRANT SELECT (`id`, `supplier_code`, `supplier_name`, `supplier_type`, `calendar_id`)
  ON `pm_db`.`m_supplier` TO 'pm_ai_view_owner'@'localhost';
-- 2. マイグレーション適用後（migrate ai 0038）、定義者を付け替える
CREATE OR REPLACE DEFINER = `pm_ai_view_owner`@`localhost` SQL SECURITY DEFINER VIEW `pm_db`.`v_ai_supplier` AS
  SELECT `id`, `supplier_code`, `supplier_name`, `supplier_type`, `calendar_id`
  FROM `pm_db`.`m_supplier`;
-- 3. 読み取りユーザーへビューのSELECTのみ付与（開発のpm_ai_readerはDB全体のSELECTを持つため、実質不要。本番はSHOW GRANTSで確認してから）
GRANT SELECT ON `pm_db`.`v_ai_supplier` TO 'pm_ai_reader'@'<本番のpm_ai_readerのホスト部。SHOW GRANTS FOR で確認>';
-- 4. 確認
SELECT TABLE_NAME, DEFINER, SECURITY_TYPE FROM information_schema.VIEWS WHERE TABLE_SCHEMA = 'pm_db' AND TABLE_NAME = 'v_ai_supplier';
SELECT COUNT(*), COUNT(DISTINCT supplier_code), SUM(supplier_type='purchase'), SUM(supplier_type='outsource'), SUM(supplier_type='both') FROM `pm_db`.`v_ai_supplier`;  -- 開発の期待値: 29, 29, 17, 9, 3
SHOW COLUMNS FROM `pm_db`.`v_ai_supplier`;  -- 5列（bigint・varchar・varchar・varchar・bigint）
SHOW GRANTS FOR 'pm_ai_view_owner'@'localhost';
```

## 20. 管理コマンド setup_ai_views（2026-10-10。BOSS承認: 案B。実装済み・evaluator未検証）

**目的**：§4.1の9番の手順（列権限の付与・定義者の付け替え）を、管理者が `migrate` の後に1回実行する管理コマンドにまとめる。MySQL固有の処理はこのコマンドに閉じ込める（マイグレーションは標準SQLのまま）。

**実装内容**（`pm_backend/apps/ai/management/commands/setup_ai_views.py`）
- 対象：定数 `SIMPLE_MASTER_VIEWS`（`v_ai_product`→`m_product`、`v_ai_process`→`m_process`、`v_ai_line`→`m_line`、`v_ai_supplier`→`m_supplier`、`v_ai_customer`→`m_customer`（§22で追加））。列は `BASE_SQL_SCHEMA[ビュー名]`（列の単一の情報源）。新しい単純なマスタビューは、この定数に1行足す。
- `v_ai_shipment`・`v_ai_purchase_receipt` は再作成しない（定義はマイグレーション0012〜0014）。`--check` で定義者を表示するだけ。
- 1ビューごとに ①`GRANT SELECT (列) ON 元テーブル TO owner`（足りない列だけ）②`CREATE OR REPLACE DEFINER = owner SQL SECURITY DEFINER VIEW`（定義者・SECURITY_TYPE・列が期待と違うときだけ）。全ビューの後に ③owner の元テーブル列権限のうち、同じ元テーブルを使う全ビューの公開列の和集合（`OTHER_VIEW_COLUMNS`：`m_product` の `id`・`product_code`・`product_name` ＝ v_ai_shipment 用、を含む）にない列を `REVOKE`。現在の権限は `information_schema.COLUMN_PRIVILEGES` から読み、差分だけを実行（冪等）。
- MySQL以外では「何もしない」と表示して終了（エラーにしない）。識別子はバッククォートで囲み、バッククォートを含む名前は拒否。ユーザー名・ホスト名は `re.fullmatch(r'[A-Za-z0-9_.%-]+')` で検査（末尾の改行も拒否）。
- 権限不足などで失敗したときは、失敗したSQLと実行済みのSQLを表示し、「管理者（rootなど）で実行する」ことを示して非0で終了。
- ビューの作り直し（CREATE）は、定義者・SECURITY_TYPE・列順のどれかが期待と違うときだけ実行する。**ビュー本体（WHERE・別名・列式・元テーブル）の違いは検出しない**（現在の4ビューは全行・結合なし・別名なしのため、実害は小さい。将来、本文の比較を足す余地がある）。
- `--check` は、owner が元テーブルに**表全体のSELECT**を持つ場合も「要対応」にする（承認内容になかった追加。表示だけで、自動では直さない。列権限がないので REVOKE も出ない）。DB全体（`SCHEMA_PRIVILEGES`）・グローバル（`USER_PRIVILEGES`）の権限は、検出しない設計。
- `--reader-host`：指定したときだけ、`pm_ai_reader` へ各ビューの `GRANT SELECT` を実行する。指定しなければ実行せず、表示だけ（開発のreaderはDB全体のSELECTを持ち、本番のホスト部は未確認のため）。
- ユーザー名・ホスト名は `re.fullmatch` で検査するため、末尾の改行も拒否する。
- 本節が参照する仕入先ビュー（`v_ai_supplier`・§19.1・マイグレーション0038）は、仕入先ビューのコミットと同時に反映する（先にコミットし、そのあとにこのコマンドをコミットする案B。BOSS承認 2026-10-10）。

**使い方**（`pm_backend` で、管理者のDB接続で実行）
```
python manage.py setup_ai_views                 # 既定: 実行予定のSQLを表示するだけ
python manage.py setup_ai_views --apply         # 実行（その後に自動で --check）
python manage.py setup_ai_views --check         # 読み取りのみの確認
```
オプション：`--owner`（既定 `pm_ai_view_owner`）、`--owner-host`（既定 `localhost`）、`--views`（対象を絞る）、`--reader-host`（指定したときだけ `pm_ai_reader` へビューのSELECTを付与。既定では実行しない。本番のホスト部は `SHOW GRANTS` で確認してから指定）。
`--check` は、定義者・SECURITY_TYPE・列（`information_schema.COLUMNS`の順序つき列名。BASE_SQL_SCHEMAと比較）・owner の列権限（公開列の和集合と一致）・`ai_reader` 接続での読み取り（`SELECT 1 FROM ビュー LIMIT 1`）を表示し、期待と違えば「要対応」と表示する。

**検証結果**
- 試験：`ai.test_setup_ai_views`（偽の接続・カーソル。DBを作らない）。生成SQLと BASE_SQL_SCHEMA・各マイグレーションの列の一致、dry-run、`--apply` の順序、不正名の拒否、MySQL以外、冪等、join系ビューの非再作成、実装を壊すと失敗すること（`OTHER_VIEW_COLUMNS` の保護・`fullmatch`・表全体のSELECTの検出・定義者／SECURITY_TYPEの比較。evaluatorが確認）、表全体のSELECTの `--check`、CREATE要否の個別条件、`--views` での絞り込み、GRANT・CREATE・REVOKE の失敗時の表示。
- 開発DB（読み取りのみ）：dry-run と `--check` を実行（2026-10-10）。`--apply` は未実行。`v_ai_supplier` の定義者が `root@localhost` で、`m_supplier` の列権限が未付与のため、dry-run は GRANT と CREATE の2文を表示した。他の3ビューは揃っている。

**未完了**：evaluatorによる検証。開発DBでの `--apply`（BOSS承認のもとで実行）。本番での実行。
**反映状況**：開発DBで、`--apply`を実機で実行済み（2026-10-10。仕入先ビューの定義者・権限を整えた。要対応0件。もう一度実行すると「実行するSQLはありません」で冪等）。本番未反映。

## 21. 得意先マスタのビュー `v_ai_customer` の作成前確認（2026-10-10。BOSS承認済み。実装は§22）

公開する列は、[AIマスタビュー確認明細](AIマスタビュー確認明細.md) §5 のBOSS判断のとおり（判断画面 decisions の `m_customer` を、草案の前に読み直した）。§4.1 の設計原則に従う。

| 確認項目 | 内容 |
|---|---|
| 業務目的 | AIが、得意先をコード・名前・略称・カレンダで、分析・説明できるようにする。出荷実績ビュー（`v_ai_shipment`）の`customer_code`から、得意先の名前を引く |
| 元テーブル | `m_customer` の1つだけ。結合なし（行数3） |
| 対象行 | 全行（絞り込みなし）。有効3 |
| 数値定義 | なし（マスタ）。件数は行数。`customer_code`は3行で重複なし |
| 公開フィールド（6列） | `id`、`customer_code`、`customer_name`、`short_name`、`calendar_id`、`is_active` |
| 非公開フィールド | `created_at`、`updated_at`（BOSS判断が未決定のため、非公開として扱う） |
| 個人情報 | なし（会社名・略称・コード）。得意先コードは個人情報ではない（運用規約 §6.5-3）。外部AIへ送る目的文の、名称→コード置換は、従来どおり（運用規約 §4.1-3） |
| 検証方法 | ①ビューの行数＝`m_customer`の行数（3）②`customer_code`の一意性③`pm_ai_reader`でビューが読め、非公開の2列が読めない④定義者が`pm_ai_view_owner@localhost`（`setup_ai_views --check`が要対応0件）⑤全行×6列が列型の検査（`_cell`）を通る⑥出荷実績ビューの`customer_code`が、すべて得意先ビューにある |

### 21.1 実データ（開発DB）
- 3行（`000018` リーデン、`000001` ティエラ、`000196` クボタ。いずれも有効）。`customer_code`は、すべて先頭がゼロで、**文字列のまま扱う**。`calendar_id`が空の得意先は0。略称は全行にある。
- 出荷実績（`t_shipment_actual`）の542行は、すべて`000196`。得意先マスタにない出荷実績の行は0件。

### 21.2 列型の対応（`m_customer`のSHOW COLUMNSからの導出。ビュー作成後に再確認する）
| 列 | MySQL型 | `ANALYSIS_COLUMN_TYPES` |
|---|---|---|
| `id`、`calendar_id` | bigint | `BIGINT` |
| `customer_code`、`customer_name`、`short_name` | varchar | `VARCHAR` |
| `is_active` | tinyint(1) | `BIGINT`（0/1） |

### 21.3 列の意味（仕様書で確認できた範囲。推測は書かない）
| 列 | 意味 | 出典 |
|---|---|---|
| `customer_code` | 得意先コード（先頭ゼロを含む文字列）。出荷実績ビューの`customer_code`と同じ文字列で結べる | 受注管理仕様書.md:51-62、開発DBの実データ |
| `customer_name`・`short_name` | 得意先名（会社名）・略称 | 項目名 |
| `calendar_id` | 得意先のカレンダ（稼働カレンダの`calendar_id`と結べる） | モデルの項目名 |
| `is_active` | 有効（1）・無効（0） | 項目名 |
| 説明文には、**具体的な得意先コード・名称を書かない**（値は、データで確認する。クボタの`000196`などの、特定の得意先を、説明に固定しない） | | 計画書 §4.1の考え方、既存の試験（説明に「000196」「クボタ」を入れない） |

### 21.4 あわせて変更するもの（実施内容は§22）
1. マイグレーション `0039`：`CREATE OR REPLACE VIEW v_ai_customer AS SELECT <6列> FROM m_customer`（標準SQLのみ）。ロールバックは`DROP VIEW IF EXISTS v_ai_customer`。
2. `setup_ai_views` の `SIMPLE_MASTER_VIEWS` に `v_ai_customer`→`m_customer` を1行追加する（権限付与・定義者の付け替えは、コマンドで行う）。
3. `ANALYSIS_VIEWS`・`ANALYSIS_COLUMN_TYPES`・`BASE_SQL_SCHEMA`・`TABLE_NOTES`・仕様書を更新する。既存ビューの列・説明は変えない。`SCREEN_SQL_TABLES`・`TERM_COLUMNS`・AIへの指示文は変更しない。元テーブル`m_customer`の許可（受注画面）は、置き換えず、ビューの追加だけにする。

### 21.5 BOSSに決めてほしいこと
- ~~公開列の6列でよいか~~ → **決定済み（承認 2026-10-10）**：6列（BOSS判断の転記どおり）。
- ~~元テーブル`m_customer`の許可は、今回は置き換えず、ビューの追加だけにしてよいか~~ → **決定済み（承認）**：置き換えず、ビューの追加だけにする。
- ~~説明文に、具体的な得意先コード・名称を書かない方針でよいか~~ → **決定済み（承認）**：書かない。

## 22. v_ai_customer 実装（2026-10-10。BOSS承認済み: §21の公開6列、元テーブルの許可は置き換えずビューの追加のみ、説明に具体的な得意先コード・名称を書かない。実装済み・evaluator未検証）

**実装内容**
- `pm_backend/apps/ai/migrations/0039_ai_customer_view.py` 新規。`CREATE OR REPLACE VIEW v_ai_customer`（6列・別名なし・WHEREなし・結合なし・標準SQLのみ）、ロールバックは`DROP VIEW IF EXISTS v_ai_customer`。依存は`ai 0038`と`masters 0001_initial`（`m_customer`の6列は、すべて`CreateModel Customer`で作成されており、後続のmastersマイグレーションでの追加・変更はない）。`makemigrations --dry-run`は「No changes detected」。
- `sql_queries.py`：`BASE_SQL_SCHEMA`に`v_ai_customer`（6列）、`TABLE_NOTES`に説明を追加。既存の`m_customer`エントリと`SCREEN_SQL_TABLES`は変更していない。
- `analysis_data_service.py`：`ANALYSIS_VIEWS`に`v_ai_customer`（label=得意先マスタ、`date_field=None`、`quantity_field=None`、説明は§21.3の範囲のみ。具体的な得意先コード・名称、`created_at`・`updated_at`は書かない）。
- `analysis_execution_service.py`：`ANALYSIS_COLUMN_TYPES`に6列（§21.2。`is_active`はtinyint(1)→BIGINT）。
- `setup_ai_views.py`：`SIMPLE_MASTER_VIEWS`に`v_ai_customer`→`m_customer`を1行追加（これ以外の変更なし）。単純なマスタビューは5つになった。
- 試験：`apps/ai/test_analysis_customer_view.py` 新規（12件）。`test_setup_ai_views.py`は、`LATEST_MIGRATION`に`v_ai_customer`→`0039_ai_customer_view.py`を追加（マイグレーションの列とBASE_SQL_SCHEMAの一致検査の対象に入る）、`--views`絞り込みの試験の「対象外の語」に`m_customer`・`v_ai_customer`を追加（検査を強める方向）。検査を弱めた箇所はない。
- 既存ビュー6つ（出荷・入荷・品番・工程・ライン・仕入先）の定義（説明・列）のJSONのSHA-256（新規試験の固定値）：`8ca47c57f9e27a60ed1822ffca227599e41056c0774c8934ba814faaaa7d2de1`。v_ai_customer の追加前（`git stash`で`services`を変更前に戻して計算）と追加後で同一。仕入先ビューの試験の既存5ビューの値（`aaed5cd7…`）は変わらず合格。
- 仕様書：`AI分析基盤仕様書.md`（公開ビュー一覧・型の対応）、`AI運用規約・AI用DB辞書.md`（§6.5-8を追加。既存の「品番・顧客コード・納入先コードの表記」は§6.5-9へ繰り下げ。他の文書・コードに§6.5-8への参照はなかった。§6.5-4の対象ビューの一覧にも追記）。

**検証結果**（開発。読み取りのみ・テスト用DBなし）
- `ai.test_analysis_customer_view`・`test_setup_ai_views`・`test_analysis_supplier_view`・`line_view`・`process_view`・`product_view`・`dateless_view`・`execution`・`planning`・`column_guide`・`codegen`・`jobs`・`multi_period`・`period_warning`・`worker_version`の1コマンド実行で304件OK（skipped=4）。フロント`pm-ui/scripts/test-analysis-*.mjs` 7本OK（codegen 68・consult 23・error-banner 6・execution 35・external-confirmation 4・status-monitor 13・templates 53、fail 0）。
- 開発DBの実データ（`AI_DB_ALIAS`接続）：`m_customer`は3行・`customer_code`は3種類（重複なし）。SHOW COLUMNS：bigint・varchar(20)・varchar(100)・varchar(40)・bigint・tinyint(1)（§21.2の対応と一致）。全3行×6列（18セル）が`_cell`を通る（エラー0件）。出荷実績ビュー`v_ai_shipment`は542行で、`customer_code`が`m_customer`にない行は0件。
- `setup_ai_views`（dry-run）：`v_ai_customer`について GRANT（`m_customer`の6列を`pm_ai_view_owner`へ）と CREATE（定義者付け替え）の2文を表示。`--check`：要対応3件（ビュー`v_ai_customer`なし・owner の`m_customer`列権限が6列とも不足・`ai_reader`接続で`v_ai_customer`が読めない）。いずれもビュー未作成による想定内。他の4つのマスタビュー・出荷・入荷は問題なし。`--apply`は実行していない。

**`setup_ai_views --apply` が実行するSQL（記録。`<db>`は接続先のDB名。MySQL固有のため、マイグレーションではなくコマンドが実行する）**
```sql
GRANT SELECT (`id`, `customer_code`, `customer_name`, `short_name`, `calendar_id`, `is_active`) ON `<db>`.`m_customer` TO 'pm_ai_view_owner'@'localhost';
CREATE OR REPLACE DEFINER = 'pm_ai_view_owner'@'localhost' SQL SECURITY DEFINER VIEW `<db>`.`v_ai_customer` AS SELECT `id`, `customer_code`, `customer_name`, `short_name`, `calendar_id`, `is_active` FROM `<db>`.`m_customer`;
```

**未完了**
- 開発DBでの`migrate ai 0039`と`setup_ai_views --apply`（BOSS承認のもとで実行）、ビュー作成後の`SHOW COLUMNS FROM v_ai_customer`と`ANALYSIS_COLUMN_TYPES`の照合。
- evaluatorによる検証。実機（AIを使う）の再試験。テスト用DBを要する`ai.test_analysis_*`は未実行。

**反映状況**：開発DBにビュー作成済み・定義者付け替え済み（2026-10-10。`migrate ai 0039`、`setup_ai_views --apply`。BOSS承認のうえ、私が実行）。確認結果：`SHOW COLUMNS FROM v_ai_customer`は6列で、型は`ANALYSIS_COLUMN_TYPES`の対応（bigint・varchar・tinyint(1)）と一致。`pm_ai_reader`の接続で、3件・コード3種類・有効3。`created_at`・`updated_at`は読めない（列がない）。全3行×6列が列型の検査を通る（エラー0）。出荷ビューの得意先コードで、得意先ビューにない行は0件。`setup_ai_views --check`は要対応0件。7つの`v_ai_`ビューの定義者は、すべて`pm_ai_view_owner@localhost`。本番未反映。

## 23. 相談の検証失敗の理由コード（2026-10-10。BOSS承認 案A・E・F・G。実装済み。案E・F・Gはevaluator条件付き合格。コミット済み 2b798827・本番未反映）

**背景**：相談（AIと目的を整える）で、OpenRouterのGemma 4 26B A4Bだけが「AIの返答を検証できませんでした。」（HTTP 502）になる。返答の中身は保存・ログ出力しない設計のため、原因を**固定の理由コードだけ**で特定できるようにする。コードブロックを許す変更（案B）は今回しない。

**実装内容**
- `analysis_consult_service.py`：`_parse`が、失敗時に固定の理由コードを付ける。（案Eの時点の記述。現行は案Gの9コード）優先順位は上から、`empty`（空・空白だけ）→`code_fence`（前後の空白を除いた先頭が```）→JSONとして読めない場合は4コードのいずれか（`json_text_before`：先頭が`{`でも`[`でもない／`json_text_after`：先頭が`{`で`raw_decode`が成功し後ろに空白以外が残る（案Fで廃止）／`json_truncated`：先頭が`{`で`exc.pos`が入力長以上、または閉じない文字列（`Unterminated string`）で終わる／`json_syntax`：それ以外。先頭が`[`で読めない場合を含む。例外の連鎖は付けない）→`json_not_object`→`reply_missing`（`reply`が文字列でない・空）。受け入れる返答の範囲は案Eの時点では変えていない（案Fで変更。下記）。
- **経緯（2026-10-10）**：Gemmaの実機で`json_invalid`と確認した。そこでBOSS承認（案E）により、`json_invalid`を廃止して上記の4コードに分けた（計8コード）。「前後の文章を許す」変更（案F）は、この時点ではしていない（その後、案Fで実施）。エラー位置の数値は判定にだけ使い、外へ出さない。
- **案F（案Fの時点の記述。`json_text_before`は案Gで廃止）（BOSS承認 2026-10-10。受け入れる範囲の変更。相談のみ。前置き・後ろの余分な文字を読み捨てる）**：Gemmaが`json_text_before`を2回続けて返したため。`empty`→`code_fence`の判定は変えない（コードブロックは拒否のまま。案Bは不採用）。その後、先頭が`[`でなく`{`を含むときは、**最初の`{`から**`raw_decode`で完全なオブジェクトとして読めた場合だけ、そのオブジェクトを使う（前後の文字は読み捨て。先頭が`{`のときの後ろの余分な文字も同じ）。使う条件は従来と同じ（`reply`が空でない文字列）。拒否のまま：最初の`{`から読めない（前置きに`{a}`など→`json_text_before`）、読めたが`reply`がない・空（`reply_missing`）、`{`がない（`json_text_before`。ただしJSONとして読める配列・文字列・数値は`json_not_object`）、先頭が`[`（従来どおり）。最初の`{`以外の`{`からは再試行しない。読み捨てた部分の中身・長さ・位置は、エラー・ログ・画面・返り値に出さない（読み捨てがあったことも出さない）。影響は`_parse`（相談）だけ。
- **案G（BOSS承認 2026-10-10。原因の確定のための理由コードの細分化。受け入れる範囲は案Fのまま）**：案F後も、Gemmaが`json_text_before`で失敗した（2026-10-10）。そこで`json_text_before`を廃止し、次の3コードに分けた。(1) `json_no_object`：`{`を全く含まず、先頭が`[`でもない（JSONで返していない）。(2) `json_prefix_truncated`：先頭が`{`でなく`{`を含み、最初の`{`からの`raw_decode`が失敗し、その失敗が入力の終わり（`exc.pos >= len(text)`、または`Unterminated string`。`json_truncated`と同じ判定）。(3) `json_prefix_brace`：先頭が`{`でなく`{`を含み、最初の`{`から読めず、入力の終わりではない（前置きの中の`{`から読めない疑い、または文法の誤り）。先頭が`{`のときの`json_truncated`・`json_syntax`、先頭が`[`のときの`json_not_object`・`json_syntax`、`reply_missing`、`empty`、`code_fence`は不変。最終は9コード（empty・code_fence・json_no_object・json_prefix_brace・json_prefix_truncated・json_truncated・json_syntax・json_not_object・reply_missing）。`json_text_before`は現行の記述から消し、試験で廃止を固定。画面の固定の説明は、`json_no_object`「AIの返答に、JSONがありませんでした」、`json_prefix_brace`「AIの返答の前の文字に `{` があり、JSONとして取り出せませんでした」、`json_prefix_truncated`「AIの返答の前に文字があり、JSONが途中で終わっていました」。位置・長さ・返答の中身は外へ出さない。
- **`json_text_after`の判断（実装で判断）**：先頭が`{`でオブジェクトが読めれば後ろは読み捨てるため、`json_text_after`が出る場面はなくなった。そこで**廃止**し、コード・画面（`PARSE_REASONS`は案F時点で7コード、案Gで9コード）・試験（廃止の固定）・仕様書を整合させた。
- **不確実な点**（案Eの時点。BOSSから未回答のため、要確認のまま）：`{"reply": "abc`のような閉じない文字列は、`JSONDecodeError.pos`が文字列の開始位置（入力長未満）になるため、指定の`exc.pos >= len(text)`だけでは`json_syntax`になってしまう。そこで`Unterminated string`も`json_truncated`に含めた（BOSS指示の例`{"reply": "abc`を`json_truncated`にするため。要確認）。
- `analysis_plan_store.py`：`AnalysisError`に省略可能な`reason`引数を追加。指定時だけ`detail`を`{detail, reason}`にし、属性`reason`を設定する（`ExecutionStopped`などの既存の`reason`を上書きしないよう、指定時だけ設定）。既存のキー・文言・ステータスは不変。
- `AIAnalysisConsult.vue`：502で`reason`が9つ（案G後。案Eは8つ、案Fは7つ）のどれかのときだけ、固定の説明を後ろに付ける（`Object.hasOwn`で限定。`json_invalid`・`json_text_after`・`json_text_before`は対象外）。
- 試験：`apps/ai/test_analysis_consult_reason.py`新規（SimpleTestCase、DBなし）。`test-analysis-consult-ui.mjs`に1件追加。
- 仕様書：`AI分析基盤仕様書.md`の5.3-3に追記。

**検証結果**（開発。DBなし）：`ai.test_analysis_consult_reason`ほか7モジュールの1コマンド実行で154件OK（skipped=2）。検証担当（evaluator）が、別の8モジュール（`ai.test_analysis_consult_reason`・`dateless_view`・`planning`・`column_guide`・`codegen`・`setup_ai_views`・`customer_view`・`execution`）で実行し、195件OK（skipped=4）。件数が違うのは、モジュールの組み合わせが違うため。フロント`test-analysis-*.mjs` 7本OK（consult 24を含む、fail 0）。途中、`AnalysisError`が無条件に`self.reason`を設定していて`ExecutionStopped`の`reason`を上書きし、既存の5件が失敗した。指定時だけ設定する形に直して解消。

**検証結果（案E後、generator実行）**：`ai.test_analysis_consult_reason`（6件）ほか7モジュールの1コマンド実行で155件OK（skipped=2）。フロント`test-analysis-*.mjs` 7本OK（consult 24、fail 0）。evaluatorの再検証は未実施。

**検証結果（案F後、generator実行）**：`ai.test_analysis_consult_reason`（7件）・`dateless_view`・`planning`・`column_guide`・`codegen`・`setup_ai_views`・`customer_view`の7モジュールの1コマンド実行で155件OK（skipped=2）。フロント`test-analysis-*.mjs` 7本OK（consult 24、fail 0）。なお上の件数は組み合わせごとに違う（generator=7モジュール、evaluator=`execution`を含む8モジュール）。evaluatorの再検証は未実施。

**案Fの既知のリスク（evaluator指摘。BOSS判断で、そのまま）**：(1) 前置きの中に、別の完全なJSONオブジェクト（`{"reply": "偽"}` など）があると、最初のオブジェクトを採用する（仕様どおり。返事は助言として表示されるだけで、実行されない。目的の文案・期間・テンプレートのIDは、サーバーが検証してから使う。緩和策は、複数のオブジェクトが読めるときに拒否することで、Gemmaの失敗が増える）。(2) 先頭が`[`でなく、配列の中にオブジェクトがある返答（`前置き [{"reply":"x"}]`）は、最初の`{`から取り出して受け入れる。(3) `前置き {"reply":"x"`（前置きあり・途中切れ）は、`json_truncated`にならない（最初の`{`から読めないため）。案Fでは`json_text_before`だったが、**案Gで`json_prefix_truncated`になる**（更新）。

**検証結果（案G後、generator実行）**：`ai.test_analysis_consult_reason`（7件）・`dateless_view`・`planning`・`column_guide`・`codegen`・`setup_ai_views`・`customer_view`の7モジュールの1コマンド実行で155件OK（skipped=2）。フロント`test-analysis-*.mjs` 7本OK（consult 24、fail 0）。evaluatorの再検証は未実施。

**検証結果（案G後、evaluator。2026-10-10）**：条件付き合格（指摘は仕様書の記述のみ。本節の追記で対応）。DBなしの8モジュールで196件OK（skipped=4）、フロント7本fail 0。実装を壊す変異7種（`json_no_object`判定の除去、prefix_truncated／prefix_braceの入れ替え、`Unterminated string`の除去、`{`を含む判定の除去、先頭`{`のjson_truncatedの置換、`from None`の除去、長さの混入）は、すべて試験が検出した。内容（`SECRET-12345`）が出る経路はなし。留意：`exc.msg`の`Unterminated string`はPythonの実装文言に依存（開発Python 3.13.5で確認、本番のバージョンは未確認）。前置きの文法の誤りでも、閉じない`"`があれば`json_prefix_truncated`になる。

**実機の結果（2026-10-10。BOSSの実機）**：OpenRouterのGemma 4 26B A4Bで、案Gの理由コードは`json_no_object`と確定した。Gemmaは、JSONで返していない（`{`が全くない）。案Fは、Gemmaには効かなかった。Qwen・DeepSeekは相談で成功。**Gemmaは相談では使わない方向（BOSS判断待ち）**。案Fを残すか外すかもBOSS判断待ち（実装担当の推奨：残す）。

**未完了**：Gemmaを相談で使わないかのBOSS判断。`Unterminated string`を`json_truncated`に含めたことのBOSS確認（要確認のまま）。本番での確認。テスト用DBを要する`test_analysis_consult.py`は未実行。

**反映状況**：コード変更のみ。コミット・本番未反映。

## 24. 稼働カレンダのビュー `v_ai_calendar_day` の実装記録（2026-10-10。BOSS承認済み。実装済み・evaluator未検証）

**承認内容**：公開12列、`m_calendar_day` を主とした `m_calendar` の LEFT JOIN、非公開列、元テーブル `m_calendar_day` の許可（4列）は置き換えずビューの追加のみ、説明に具体的なカレンダコード・名称・件数を書かない。

**元と結合**：`m_calendar_day`（別名 `d`）を主とし、`LEFT JOIN m_calendar c ON c.id = d.calendar_id`。結合の理由は**マスタ属性（カレンダのコード・名称・区分）の付与のみ**。結合先は `m_calendar` の主キー（`id`）のため、1対1で行数は `m_calendar_day` と変わらない。WHEREなし（ビューとしては全行）。標準SQLのみ（バッククォート・DEFINER・SQL SECURITY・DB修飾なし）。

**公開列（12列。この順）**
| # | 列 | 元 | ANALYSIS_COLUMN_TYPES |
|---|---|---|---|
| 1 | `id` | `d.id` | BIGINT |
| 2 | `calendar_id` | `d.calendar_id` | BIGINT |
| 3 | `calendar_code` | `c.calendar_code` | VARCHAR |
| 4 | `calendar_name` | `c.calendar_name` | VARCHAR |
| 5 | `calendar_type` | `c.calendar_type` | VARCHAR |
| 6 | `target_date` | `d.target_date` | DATE |
| 7 | `is_working_day` | `d.is_working_day`（真偽値） | BIGINT（0/1） |
| 8 | `is_delivery_day` | `d.is_delivery_day`（真偽値） | BIGINT（0/1） |
| 9 | `is_order_day` | `d.is_order_day`（真偽値） | BIGINT（0/1） |
| 10 | `is_holiday_work` | `d.is_holiday_work`（真偽値） | BIGINT（0/1） |
| 11 | `work_minutes` | `d.work_minutes`（稼働分。分。空を許す） | BIGINT |
| 12 | `work_pattern_id` | `d.work_pattern_id`（勤務パターンのID。空を許す） | BIGINT |

型は、モデル（`masters/models.py`）とマイグレーションから導出（`BigAutoField`・外部キー→bigint、`BooleanField`→tinyint(1)→BIGINT、`IntegerField`→int→BIGINT、`DateField`→DATE、`CharField`→VARCHAR）。ビュー作成後に `SHOW COLUMNS FROM v_ai_calendar_day` と照合する（未実施）。

**非公開（ビューに含めない）**：`m_calendar_day` の `note`・`created_at`・`updated_at`。`m_calendar` の上記3列（`calendar_code`・`calendar_name`・`calendar_type`）以外の列。

**未決定扱いの `m_calendar` の列**：`is_line_assignable`（ライン割当可）・`is_supplier_assignable`（仕入先割当可）・`description`（説明）・`created_by`・`updated_by`・`created_at`・`updated_at`。公開するかBOSS判断が未決定のため、非公開。カレンダマスタ単独のビュー `v_ai_calendar` は後回し（今回は作らない）。

**列の意味（確認できた範囲だけ。推測は書かない）**：稼働日・納入日・発注日・休日出勤は真偽値（モデルの項目名）。`work_minutes` は稼働分（分）。`calendar_type` の選択肢はモデルのラベル（INTERNAL=社内、SUPPLIER=仕入れ、COMPANY=会社、CUSTOMER=顧客、OTHER=その他）。`calendar_id` は line／supplier／customer ビューの `calendar_id` と結べる。各区分、および納入日・発注日・休日出勤・勤務パターンの業務上の意味は「未確認」と説明に書いた。説明に具体的なカレンダコード・名称・件数・期間は書いていない。

**実装内容**
- `pm_backend/apps/ai/migrations/0040_ai_calendar_day_view.py` 新規。`CREATE OR REPLACE VIEW v_ai_calendar_day`、逆は `DROP VIEW IF EXISTS v_ai_calendar_day`。依存は `ai 0039_ai_customer_view` と `masters 0086_add_is_order_day_to_calendar_day`（元の列の追加：`calendar_type`=0057、`work_pattern_id`=0016、`is_holiday_work`=0074、`is_delivery_day`=0075、`is_order_day`=0086）。`makemigrations` は不要（RunSQLのみ）。
- `sql_queries.py`：`BASE_SQL_SCHEMA` に `v_ai_calendar_day`（12列）、`TABLE_NOTES` に説明を追加。既存の `m_calendar_day`（4列）と `SCREEN_SQL_TABLES` は変更していない。
- `analysis_data_service.py`：`ANALYSIS_VIEWS` に `v_ai_calendar_day`（label=稼働カレンダ、`date_field='target_date'`、`quantity_field=None`）。
- `analysis_execution_service.py`：`ANALYSIS_COLUMN_TYPES` に12列。
- `setup_ai_views.py`：`EXISTING_JOIN_VIEWS` に `v_ai_calendar_day` を追加（`v_ai_shipment` と同様の結合ビュー扱い＝再作成せず `--check` で定義者を表示）。`OTHER_VIEW_COLUMNS` に `m_calendar_day`（9列）・`m_calendar`（4列）を追加。**このコマンドは、結合ビューの GRANT・定義者の付け替えを実行しない**（下記の手順SQLを手動で実行）。
- 試験：`apps/ai/test_analysis_calendar_day_view.py` 新規。`test_setup_ai_views.py` に結合ビュー扱いの試験を1件追加。

**既存の customer／line との違い（期間指定の挙動）**：`date_field='target_date'`（日付あり）のため、**期間で絞って取得する**（`WHERE target_date >= 開始 AND target_date <= 終了`）。`fields` に `target_date` を含める必要がある（検証でエラーになる）。日付なしの customer・line・supplier・product・process は期間で絞らず全行。承認画面の件数は `period_applied=true`。

**手順SQL（`pm_ai_view_owner` への列権限と定義者の付け替え。MySQL固有のため、マイグレーションではなく手動。実行はBOSS。`<db>`は接続先のDB名。管理者で実行）**
```sql
GRANT SELECT (`id`, `calendar_id`, `target_date`, `is_working_day`, `is_delivery_day`, `is_order_day`, `is_holiday_work`, `work_minutes`, `work_pattern_id`) ON `<db>`.`m_calendar_day` TO 'pm_ai_view_owner'@'localhost';
GRANT SELECT (`id`, `calendar_code`, `calendar_name`, `calendar_type`) ON `<db>`.`m_calendar` TO 'pm_ai_view_owner'@'localhost';
CREATE OR REPLACE DEFINER = 'pm_ai_view_owner'@'localhost' SQL SECURITY DEFINER VIEW `<db>`.`v_ai_calendar_day` AS SELECT d.`id`, d.`calendar_id`, c.`calendar_code`, c.`calendar_name`, c.`calendar_type`, d.`target_date`, d.`is_working_day`, d.`is_delivery_day`, d.`is_order_day`, d.`is_holiday_work`, d.`work_minutes`, d.`work_pattern_id` FROM `<db>`.`m_calendar_day` d LEFT JOIN `<db>`.`m_calendar` c ON c.`id` = d.`calendar_id`;
GRANT SELECT ON `<db>`.`v_ai_calendar_day` TO 'pm_ai_reader'@'<readerのホスト部>';  -- 開発のreaderがDB全体のSELECTを持つ場合は不要
```

**検証結果**（generator実行。DBなし・読み取りのみ）：`ai.test_analysis_calendar_day_view`・`customer_view`・`line_view`・`supplier_view`・`process_view`・`product_view`・`dateless_view`・`setup_ai_views`・`planning`・`column_guide`・`codegen`・`execution` の1コマンド実行で247件OK（skipped=4）。フロント `test-analysis-*.mjs` 7本OK（codegen 68・consult 24・error-banner 6・execution 35・external-confirmation 4・status-monitor 13・templates 53、fail 0）。既存6ビューの定義JSONのSHA-256は `8ca47c57…`（得意先ビュー実装時と同じ）のまま。evaluatorの検証は未実施。

**検証結果（evaluator。2026-10-10）**：条件付き合格（不具合なし）。DBなしの12モジュール247件OK（skipped=4）、フロント7本fail 0、変異10通りすべて検出。開発DBの読み取りで、`m_calendar_day`＝8,479行、`m_calendar`をLEFT JOINしても8,479行（増えない）、`m_calendar`にない`calendar_id`の行は0件。

**開発DBでの実施（BOSS承認「はい」。2026-10-10）**：`migrate ai 0040` と、上の手順SQL（`m_calendar_day`の9列・`m_calendar`の4列のGRANT、`CREATE OR REPLACE DEFINER = pm_ai_view_owner@localhost SQL SECURITY DEFINER VIEW`）を実行した。`information_schema.VIEWS`で定義者`pm_ai_view_owner@localhost`・`DEFINER`を確認。`setup_ai_views --check` は要対応0件（`ai_reader`接続で`v_ai_calendar_day`が読める）。`ai_reader`接続で、件数8,479、`SHOW COLUMNS`の12列の型が`ANALYSIS_COLUMN_TYPES`と整合（bigint→BIGINT、varchar→VARCHAR、date→DATE、tinyint(1)→BIGINT、int→BIGINT）、非公開列`created_at`は読めないことを確認。「全行×12列が列型の検査を通ること」は、分析の実行経路ではまだ試していない。

**未完了**：実機（AIを使う）での再試験。分析の実行経路での全行×12列の型検査。結合ビューのGRANT・定義者の付け替えを`setup_ai_views`で自動化するか（BOSS判断待ち）。

**反映状況**：コミット済み（0259a4c4）。**開発DBへ反映済み**（`migrate ai 0040`＋手順SQLの手動実行。`setup_ai_views --apply`は使っていない＝結合ビューは対象外）。本番未反映。

## 25. BOM明細のビュー `v_ai_bom_item` の作成前確認（2026-10-10。BOSS承認済み: 公開29列、`bom_`の接頭辞、元テーブル`m_bom`・`m_bom_item`の許可は置き換えずビューの追加のみ。実装はgeneratorが実施）

公開する列は、判断画面 decisions の `m_bom`・`m_bom_item` を、草案の前に読み直して決めた（`m_bom` は7列すべて公開、`m_bom_item` は13列を公開。非公開は `remark`、`created_at`・`updated_at` は判断が未決定のため非公開）。

### 25.1 BOSSの決定事項（この草案の前提）
| 決定 | 内容 |
|---|---|
| ①明細を主にしてヘッダを結合 | `m_bom_item` を主テーブルにし、`m_bom` を `LEFT JOIN`。§3（41行目）の「ヘッダと明細は別ビュー」と §4.1-2「結合してよいのはマスタの属性を付けるときだけ」の**例外**とする（BOSS承認 2026-10-10）。ヘッダは `bom_id` の主キー結合のため、行数は明細と変わらない。承認後に、41行目と §4.1-2 へこの例外を追記する |
| 品番・工程・ライン・仕入先も結合 | 親品番・子品番（`m_product`）、`m_process`、`m_line`、`m_supplier` のコードと名称を `LEFT JOIN` で付ける（BOSS指示 2026-10-10） |
| ヘッダ単独のビューは作らない | `v_ai_bom` は作らない。明細が1行もないBOM9件はビューに出ない。9件の中身は「とりあえず作らない」＝保留（BOSS指示 2026-10-10） |
| 結合ビューの手順は手動（案A） | `setup_ai_views` の自動化はしない。GRANT・定義者の付け替えは、§25.6 の手順SQLをBOSSが実行する |

### 25.2 確認項目
| 確認項目 | 内容 |
|---|---|
| 業務目的 | AIが、BOM（親品番に対する子品番・員数・調達区分・工程・ライン・仕入先・リードタイム）を、コードと名称で分析・説明できるようにする |
| 元テーブル | 主：`m_bom_item`（別名 `i`）。`LEFT JOIN m_bom b ON b.id = i.bom_id`、`LEFT JOIN m_product pp ON pp.id = b.parent_product_id`、`LEFT JOIN m_product cp ON cp.id = i.child_product_id`、`LEFT JOIN m_process pr ON pr.id = i.process_id`、`LEFT JOIN m_line l ON l.id = i.line_id`、`LEFT JOIN m_supplier s ON s.id = i.supplier_id`。結合先はすべて主キー（`id`）のため、行数は `m_bom_item` と同じ（BOSSが実行したSQLの結果：明細3,428行。開発DBの結果） |
| 対象行 | 全行（WHEREなし）。ヘッダのない明細は残る（LEFT JOIN）。**明細のないBOM9件（ヘッダ1,323件中）は、ビューに出ない**。このため、このビューでBOMの件数を数えると、実際より9件少ない（説明に書く） |
| 数値定義 | `quantity`は、親1個あたりの子の数量（受注展開仕様書 Step2）。1行=BOM明細1行。`quantity`を行をまたいで合計しても業務上の意味はない（`quantity_field=None`） |
| 日付の列 | `bom_valid_from`・`bom_valid_to`はBOMの有効期間であり、実績の日付ではない。`date_field=None`（期間では絞らず、全行を対象にする。既存のマスタビューと同じ） |
| 個人情報 | なし（コード・名称・数量）。仕入先の担当者名・電話・メールは結合しない（`v_ai_supplier`と同じ公開列だけ） |

### 25.3 公開列（29列。この順）
| # | 列 | 元 | ANALYSIS_COLUMN_TYPES |
|---|---|---|---|
| 1 | `id` | `i.id` | BIGINT |
| 2 | `bom_id` | `i.bom_id` | BIGINT |
| 3 | `parent_product_id` | `b.parent_product_id` | BIGINT |
| 4 | `parent_product_code` | `pp.product_code` | VARCHAR |
| 5 | `parent_product_name` | `pp.product_name` | VARCHAR |
| 6 | `bom_version` | `b.version` | VARCHAR |
| 7 | `bom_valid_from` | `b.valid_from` | DATE |
| 8 | `bom_valid_to` | `b.valid_to`（空を許す） | DATE |
| 9 | `bom_is_active` | `b.is_active`（真偽値） | BIGINT（0/1） |
| 10 | `bom_is_coproduct` | `b.is_coproduct`（真偽値） | BIGINT（0/1） |
| 11 | `child_product_id` | `i.child_product_id` | BIGINT |
| 12 | `child_product_code` | `cp.product_code` | VARCHAR |
| 13 | `child_product_name` | `cp.product_name` | VARCHAR |
| 14 | `quantity` | `i.quantity`（decimal(12,3)） | DECIMAL(18,3) |
| 15 | `loss_rate` | `i.loss_rate`（decimal(5,3)。空を許す） | DECIMAL(18,3) |
| 16 | `sourcing_type` | `i.sourcing_type` | VARCHAR |
| 17 | `supplier_id` | `i.supplier_id`（空を許す） | BIGINT |
| 18 | `supplier_code` | `s.supplier_code` | VARCHAR |
| 19 | `supplier_name` | `s.supplier_name` | VARCHAR |
| 20 | `process_id` | `i.process_id`（空を許す） | BIGINT |
| 21 | `process_code` | `pr.process_code` | VARCHAR |
| 22 | `process_name` | `pr.process_name` | VARCHAR |
| 23 | `line_id` | `i.line_id`（空を許す） | BIGINT |
| 24 | `line_code` | `l.line_code` | VARCHAR |
| 25 | `line_name` | `l.line_name` | VARCHAR |
| 26 | `time_unit` | `i.time_unit` | VARCHAR |
| 27 | `lead_time_days` | `i.lead_time_days` | BIGINT |
| 28 | `duration_min` | `i.duration_min`（空を許す） | BIGINT |
| 29 | `is_coproduct_driver` | `i.is_coproduct_driver`（真偽値） | BIGINT（0/1） |

ヘッダ由来の列には `bom_` を付けた（`is_active`などが明細の列と紛らわしいため。列名はBOSSが変更してよい）。型は、モデル（`masters/models.py:384-445`）から導出した（`BigAutoField`・外部キー→bigint、`DecimalField(p,s)`→`DECIMAL(18,s)`、`BooleanField`→BIGINT、`IntegerField`→BIGINT、`DateField`→DATE、`CharField`→VARCHAR）。ビュー作成後に `SHOW COLUMNS FROM v_ai_bom_item` と照合する（未実施）。

**非公開（ビューに含めない）**：`m_bom_item.remark`（備考。BOSS判断で非公開）、`created_at`・`updated_at`（判断が未決定のため非公開）。`m_bom.created_at`・`updated_at`（同）。結合先の品番・工程・ライン・仕入先は、コード・名称以外の列を持ち込まない（仕入先の担当者・電話・メールを含む）。

### 25.4 列の意味（仕様書とコードで確認できた範囲。推測は書かない）
| 列 | 意味 | 出典 |
|---|---|---|
| `bom_version`・`bom_valid_from`・`bom_valid_to`・`bom_is_active` | 版・有効開始日・有効終了日・有効。計画日が`valid_from`以降かつ`valid_to`以前（空は期限なし）のBOMを使い、複数あれば`valid_from`が新しいものを優先する | `gantt_planning.py:565-568,595-598,769-770`、モデルの項目名 |
| `bom_version` | 版。値は`v1`・`v2`・`v_auto_日付_番号`（自動で作られた版）の3種類（BOSSが実行したSQLの結果）。最新のBOMは、版ではなく**有効開始日**で決める（有効開始日を優先。BOSS指示 2026-10-10）。計画でBOMを選ぶコードも、有効開始日の新しい順 | BOSS指示、`gantt_planning.py:568,598` |
| `bom_is_coproduct` | 連産品BOM。1つの工程で複数の製品が同時に生産されるBOM（親製品は仮想セット品番）。受注展開のBOM倍率計算・在庫計算から除外される | モデルの説明文、受注展開仕様書.md:213,530 |
| `is_coproduct_driver` | 連産品代表品。連産親品番から代表の子品番を決めるときに使う | `gantt_planning.py:582,609,780` |
| `quantity` | 親1個あたりの子の数量（員数） | 受注展開仕様書.md Step2（部品B=2個の例） |
| `loss_rate` | ロス率。空でないとき、数量に (1+ロス率) を掛ける（比率。%ではない） | `gantt_planning.py:750-751` |
| `sourcing_type` | 調達区分：MAKE=自社製造、BUY=購買、SUBCON=外注。BUY・SUBCONで仕入先が決まっている明細が購買の対象。MAKEの明細がルーティング草案の対象 | モデルのラベル、`scheduling_logic_v3.md:229,413` |
| `supplier_id`・`process_id`・`line_id` | 明細の仕入先・工程・ライン（空の明細がある）。それぞれ`v_ai_supplier`・`v_ai_process`・`v_ai_line`の`id`と結べる | モデル、各ビュー |
| `process_code` | `G`は外作、`PURCHASE`は購買を示すための工程（実際の工程ではない） | §13、BOSS指示 |
| `time_unit`・`duration_min` | 時間単位（DAY=日、MINUTE=分）と所要時間（分）。`duration_min`は加工時間（サイクル時間）で、`lead_time_days`が1以上の行にも入りうる | モデルのラベル、`scheduling_logic_v3.md:414`、BOSS回答（2026-10-10）、リードタイム仕様書.md:38 |
| `lead_time_days` | リードタイム（日）。親→子の需要日シフトに使う。ルーティング工程とラインのリードタイムが無いときの最後の候補 | リードタイム仕様書.md:15,33 |
| `child_product_id`・`parent_product_id` | 子・親の品番ID。`v_ai_product`の`id`と結べる | モデル、§9 |

**実データ（BOSSが実行したSQLの結果。2026-10-10。開発DB。明細3,428行）**
| 調達区分 | 時間単位 | 行数 | 工程あり | ラインあり | 仕入先あり | `lead_time_days`が1以上 | `duration_min`が1以上 |
|---|---|---|---|---|---|---|---|
| MAKE | DAY | 553 | 553 | 553 | 0 | 553 | 0 |
| MAKE | MINUTE | 1,355 | 1,355 | 1,355 | 0 | 401 | 1,355 |
| BUY | DAY | 684 | 12 | 12 | 684 | 684 | 0 |
| SUBCON | DAY | 681 | 681 | 573 | 681 | 681 | 1 |
| SUBCON | MINUTE | 155 | 155 | 155 | 155 | 154 | 155 |

版の値は、`v1`＝1,317件、`v_auto_20260313_2`＝4件、`v2`＝2件（計1,323件）。

**実データから言えること（現時点の状態。BOSSの回答「現在のデータはよくない。後で直す」（2026-10-10）のため、説明文には書かない。説明文は、BOSSの回答の業務ルールだけを書き、ビューは入っている値をそのまま見せる）**：MAKEは、工程・ラインが必ずあり、仕入先はない。BUYは、仕入先が必ずあり、工程・ラインがあるのは684行中12行だけ。SUBCONは、工程と仕入先が必ずあり、ラインは836行中728行にある（時間単位がMINUTEの155行はすべてあり、DAYの681行中573行）。時間単位がDAYの行は、`lead_time_days`を使い（DAYの1,918行はすべて1以上）、`duration_min`はほぼ空または0（1行だけ1以上）。MINUTEの行は、`duration_min`が必ず1以上。`lead_time_days`は、MAKEのMINUTEで401/1,355行、SUBCONのMINUTEで154/155行が1以上。`lead_time_days`が0の行は、ありえる（BOSS回答。リードタイム仕様書でも0は有効値）。

**BOSSの回答（2026-10-10。実データの疑問点への回答）**
- BUY（購買）は、仕入先だけでよい。工程・ラインがある12行は、本来は不要（BOSS回答の理解。要確認）。
- SUBCON（外注）は、仕入先が必ずある（BOSS回答。実データも836行すべてに仕入先がある）。工程・ラインについては、BOSSの回答はまだない（実データは、工程が836行すべて、ラインが728行にある）。
- 時間単位がDAYの行も、MINUTEの行も、リードタイム（`lead_time_days`）と加工時間（サイクル時間。`duration_min`）の両方を持つ、として扱う（BOSS回答 2026-10-10）。リードタイム仕様書.md:38 も、`duration_min`をサイクルタイム専用とし、LT日数のシフトには使わないとしている。
- **ただし実データでは**、DAYの行（1,918行）は`duration_min`が入っていない行がほとんど（1以上は1行だけ。0と空の区別は未確認）。MINUTEの行（1,510行）は`duration_min`が全行1以上で、`lead_time_days`が1以上なのは一部（MAKE 401/1,355行、SUBCON 154/155行）。説明には、BOSSの回答（両方を持つ）と、実データの状態（DAYの行は加工時間が入っていないことが多い）を、分けて書く。
- 版`v_auto_…`（4件）は、自動作成したBOM。

**未確認（説明に「業務上の意味は未確認」と書く）**：上のBOSS回答のうち「要確認」とした2点の解釈。明細のないBOM9件の中身は、BOSS指示（2026-10-10）で「とりあえず作らない」＝保留とし、調べない。説明文には、具体的な品番コード・名称・件数を書かない。

### 25.5 実装内容（承認後。generatorが行う）
1. `pm_backend/apps/ai/migrations/0041_ai_bom_item_view.py` 新規。`CREATE OR REPLACE VIEW v_ai_bom_item AS SELECT …`（標準SQLのみ。バッククォート・DEFINER・SQL SECURITY・DB修飾なし）。ロールバックは`DROP VIEW IF EXISTS v_ai_bom_item`。依存は`ai 0040_ai_calendar_day_view`と、元の列が揃う`masters`の最新マイグレーション（`is_coproduct_driver`＝0029、`is_coproduct`＝0013。generatorが現行の最新を確認する）。`makemigrations`は不要。
2. `sql_queries.py`：`BASE_SQL_SCHEMA`に`v_ai_bom_item`（29列）、`TABLE_NOTES`に説明を追加。
3. `analysis_data_service.py`：`ANALYSIS_VIEWS`に`v_ai_bom_item`（label=BOM明細、`date_field=None`、`quantity_field=None`、説明は§25.4の確認済みの範囲だけ。明細のないBOMが出ないことを含む）。
4. `analysis_execution_service.py`：`ANALYSIS_COLUMN_TYPES`に29列。
5. `setup_ai_views.py`：`EXISTING_JOIN_VIEWS`に`v_ai_bom_item`を追加（再作成せず`--check`で定義者を表示）。`OTHER_VIEW_COLUMNS`に`m_bom`（`id`・`parent_product_id`・`version`・`valid_from`・`valid_to`・`is_active`・`is_coproduct`の7列）と`m_bom_item`（`remark`・`created_at`・`updated_at`以外の13列）を追加する。品番・工程・ライン・仕入先の列は、既存の単純ビューが同じ列を使う。**コマンドの動作（GRANT・定義者の付け替え）は変えない**（案A）。
6. 試験：`apps/ai/test_analysis_bom_item_view.py`新規（`test_analysis_calendar_day_view.py`と同じ形式。DBなし）。既存ビューの定義のSHA-256を更新する。
7. 変更しないもの：既存の元テーブル`m_bom`・`m_bom_item`の許可（`SCREEN_SQL_TABLES`）、既存ビューの列・説明、`setup_ai_views`の動作。

### 25.6 手順SQL（`pm_ai_view_owner`への列権限と定義者の付け替え。MySQL固有のため手動。実行はBOSS。`<db>`は接続先のDB名。管理者で実行）
```sql
GRANT SELECT (`id`, `parent_product_id`, `version`, `valid_from`, `valid_to`, `is_active`, `is_coproduct`) ON `<db>`.`m_bom` TO 'pm_ai_view_owner'@'localhost';
GRANT SELECT (`id`, `bom_id`, `child_product_id`, `quantity`, `loss_rate`, `sourcing_type`, `supplier_id`, `process_id`, `line_id`, `time_unit`, `lead_time_days`, `duration_min`, `is_coproduct_driver`) ON `<db>`.`m_bom_item` TO 'pm_ai_view_owner'@'localhost';
-- m_product・m_process・m_line・m_supplier のコード・名称の列は、setup_ai_views --apply で付与済みの場合は不要(未付与なら先に実行)
CREATE OR REPLACE DEFINER = 'pm_ai_view_owner'@'localhost' SQL SECURITY DEFINER VIEW `<db>`.`v_ai_bom_item` AS
SELECT i.`id`, i.`bom_id`, b.`parent_product_id`, pp.`product_code` AS `parent_product_code`, pp.`product_name` AS `parent_product_name`,
       b.`version` AS `bom_version`, b.`valid_from` AS `bom_valid_from`, b.`valid_to` AS `bom_valid_to`, b.`is_active` AS `bom_is_active`, b.`is_coproduct` AS `bom_is_coproduct`,
       i.`child_product_id`, cp.`product_code` AS `child_product_code`, cp.`product_name` AS `child_product_name`,
       i.`quantity`, i.`loss_rate`, i.`sourcing_type`,
       i.`supplier_id`, s.`supplier_code`, s.`supplier_name`,
       i.`process_id`, pr.`process_code`, pr.`process_name`,
       i.`line_id`, l.`line_code`, l.`line_name`,
       i.`time_unit`, i.`lead_time_days`, i.`duration_min`, i.`is_coproduct_driver`
FROM `<db>`.`m_bom_item` i
LEFT JOIN `<db>`.`m_bom` b ON b.`id` = i.`bom_id`
LEFT JOIN `<db>`.`m_product` pp ON pp.`id` = b.`parent_product_id`
LEFT JOIN `<db>`.`m_product` cp ON cp.`id` = i.`child_product_id`
LEFT JOIN `<db>`.`m_process` pr ON pr.`id` = i.`process_id`
LEFT JOIN `<db>`.`m_line` l ON l.`id` = i.`line_id`
LEFT JOIN `<db>`.`m_supplier` s ON s.`id` = i.`supplier_id`;
GRANT SELECT ON `<db>`.`v_ai_bom_item` TO 'pm_ai_reader'@'<readerのホスト部>';  -- 開発のreaderがDB全体のSELECTを持つ場合は不要
```
手順SQLのビュー定義は、マイグレーション0041のSELECT（標準SQL）と、列・結合・別名が同じであること（検証項目8）。

### 25.7 検証項目（合否が機械的に判定できるもの）
1. ビューの行数＝`m_bom_item`の行数（BOSSが実行したSQLでは3,428）。
2. `COUNT(DISTINCT bom_id)`＝ヘッダ件数−明細のないBOM件数（1,323−9＝1,314）。
3. `m_bom_item`の`bom_id`がヘッダにない行が0件（BOSSの確認SQL 3）。ある場合は、その行は`bom_*`の列が空になることを説明に書く。
4. 品番・工程・ライン・仕入先の結合で、コードが空になる行の件数が、元のIDがあるのにマスタにない行の件数（BOSSの確認SQL 4）と一致する。
5. `pm_ai_reader`の接続でビューが読め、非公開列（`remark`・`created_at`・`updated_at`）は読めない。
6. 定義者が`pm_ai_view_owner@localhost`・`DEFINER`（`setup_ai_views --check`の要対応が0件）。
7. 全行×29列が列型の検査を通る（分析の実行経路で確認）。
8. マイグレーションのSELECTと§25.6の手順SQLのSELECTが、列・結合・別名で同じ。
9. 既存ビュー（8本）の定義・列・説明が変わっていない（定義のSHA-256）。
10. 説明文に、具体的な品番コード・名称・件数がない。「未確認」の項目が§25.4と一致する。

### 25.8 BOSS判断の記録
- ~~公開列の29列でよいか~~ → **決定済み（承認 2026-10-10）**：29列。
- ~~ヘッダ由来の列に`bom_`を付ける案でよいか~~ → **決定済み（承認）**：付ける。
- ~~元テーブル`m_bom`・`m_bom_item`の許可は、置き換えず、ビューの追加だけにしてよいか~~ → **決定済み（承認）**：置き換えず、ビューの追加だけにする。
- 確認SQLの結果は、開発DBのもの（BOSS回答 2026-10-10）。
- 現在のデータはよくなく、BOSSが後で直す（説明文には実データの件数・傾向を書かない。§25.4）。
- 明細のないBOM9件の中身は、保留（とりあえず作らない。調べない）。

**未確認のまま実装に進む項目**：確認SQL 3（明細の`bom_id`がヘッダにない行の件数）・4（品番・工程・ライン・仕入先がマスタにない行の件数）の結果は、まだない。実装後の検証（§25.7 の3・4）で、開発DBの読み取りにより確認する。

### 25.9 反映状況
**【現状（2026-10-11 更新）】コミット済み（69cc76e8・82f2d261・a006e417。main 4facef1c に取り込み・push 済み）。開発DBへ反映済み**：`migrate ai 0041` と §25.6 の手順SQL（GRANT 2文＋CREATE OR REPLACE。定義者 `pm_ai_view_owner@localhost`・DEFINER、`setup_ai_views --check` 要対応0件）。**evaluator（独立検証）：条件付き（コード・開発DBは合格、条件は仕様書の更新漏れのみ→本更新で対応）**。DBなしの13モジュール263件OK（skipped=4）、フロント7本fail 0、変異38通り中36通りを検出（検出できなかったのは日本語の固有名詞と漢数字の件数で、正規表現による試験の限界）。開発DB（読み取りのみ）：行数3,428＝`m_bom_item`、`COUNT(DISTINCT bom_id)`＝1,314、`bom_id`のヘッダ欠損0、結合先の欠損0、`ai_reader`で全3,428行×29列が実行経路の型検査（`_cell`）を通る、`remark`・`created_at`・`updated_at`はビューで読めない。**未確認**：判断ページ本体との照合（ローカルの確認明細との一致まで）、DuckDBへの実投入、本番の`pm_ai_reader`の権限（開発の`pm_ai_reader`はDB全体のSELECTを持つため、基底テーブルの`remark`等は開発では読める）、本番反映。既存ビューの定義JSONのSHA-256（`db31acbf…`）は7ビュー（`v_ai_calendar_day`を含む。§25.7の「8本」は本ビューを足した数）。**BOSS判断待ち**：説明文に残る`v_auto_…`の版の値の記載と、`process_code`のG・PURCHASEの具体コードを残すか（出典はBOSS回答。現状は残す）。以下は実装時点（2026-10-11）の記録：BOSS承認済み。**evaluator（2026-10-11）：条件付き→修正後の再検証（1回め）で合格（DBなしで確認できる項目8・9・10と観点2〜8）。DBが必要な項目1〜7は未確認**。初回の指摘（説明文に版の値・種類数がある／未確認の範囲のずれ／試験が甘い）は、BOSS承認「削る案」で修正済み。説明文には実データの件数・傾向・版の値を書かない。試験は、DBなしの環境差し替え（sqlite）で、新規・関連49件OK。`codegen`・`execution`などの115件の失敗は、`ai_reader`設定がない環境要因で、変更前のコードでも名前まで同一（新ビューが原因の失敗なし。本来の設定では未実行）。**コード実装済み（generator）**：`0041_ai_bom_item_view.py`・`sql_queries.py`・`analysis_data_service.py`・`analysis_execution_service.py`・`setup_ai_views.py`（`EXISTING_JOIN_VIEWS`・`OTHER_VIEW_COLUMNS`のみ）・`test_analysis_bom_item_view.py`（新規）・`test_setup_ai_views.py`（1件追加）。既存7ビューの定義のSHA-256は変わらず（`db31acbf…`のまま）。DBなしの試験は実行済み（`ai.test_analysis_bom_item_view`ほか10モジュール132件OK）。**開発DBは未変更**（`migrate ai 0041`・§25.6の手順SQLは未実行＝BOSSが実行）。§25.7の検証項目（DB上の確認）は未実施。41行目・§4.1-2への例外の追記は実施済み（BOSS承認 2026-10-11。未コミット）。`lead_time_days`の説明の1文（親→子の需要日をずらすときに使う）と、§25.4の版の実データは、BOSS判断で残す（2026-10-11）。開発DBへの反映（`migrate ai 0041`と手順SQL）は、BOSSが実行する段階（2026-10-11 手順を提示）。本番未反映。

## 26. ルーティングのビュー `v_ai_routing_step`・`v_ai_routing_step_material` の作成前確認（2026-10-11。BOSS承認済み。実装済み・evaluator(2026-10-11)条件付き→指摘修正済み。開発DB反映済み・本番未反映。実装記録は§26.8）

公開する列は、判断画面 decisions の `m_routing`・`m_routing_step`・`m_routing_step_material` を、草案の前に読み直して決めた（2026-10-11 時点で、判断ページに `step_type`・`created_at`・`updated_at` の記載はない＝非公開として扱う）。

### 26.1 BOSSの回答（2026-10-11）
- 結合できるか → 1つのビューにまとめると、1工程に複数の材料があるため行が増える（材料の行6,421件・最大123件/工程。材料のない工程5,011件）。**2つのビューに分け、各ビューは「結合先の主キーでのLEFT JOIN」だけにする**（工程7,678行・材料6,421行）。
- 工程のビューは、加工後品（id・コード・名称）と親品（コード）が分かればよい。**親品のidは出さない**（AIは `parent_product_code` を `v_ai_product.product_code` と結べる。BOSS承認「hai」）。
- 使用個数は、工程の列ではなく、**親の工程の材料の数量から求める値の一つ**（画面 `RoutingMaster.vue` の `usageQuantity`。ただし**画面の使用個数と同じとは限らない**。§26.4）。材料のビューの `quantity` として持たせ、説明文で補う（案2a）。材料のビューも今回作る（案3a）。
- ヘッダ単独の `v_ai_routing`（`m_routing`、540行）は、**調べてから決める**（今回は作らない）。
- `step_type`（`m_routing_step`、開発DBの実値は `FLOW` 7,678行・`PARALLEL_POOL` 0行。モデルになく仕様書にも説明なし）は、**業務上の意味は未確認・非公開**。
- 材料のない工程の業務上の意味は**未確認**（購買・レーザ1・外作の工程に多い。442ルーティングは材料なし、98は混在）。

### 26.2 `v_ai_routing_step`（工程。33列。`m_routing_step` を主とし、すべて主キーのLEFT JOIN。行数＝工程数）
`id`, `routing_id`, `routing_code`, `routing_product_id`, `routing_product_code`, `routing_product_name`, `routing_is_default`, `routing_is_active`, `routing_valid_from_datetime`, `routing_valid_to_datetime`, `step_no`, `parallel_group`, `parallel_count`, `hierarchy_depth`, `hierarchy_path`, `process_id`, `process_code`, `process_name`, `line_id`, `line_code`, `line_name`, `supplier_id`, `supplier_code`, `supplier_name`, `output_product_id`, `output_product_code`, `output_product_name`, `parent_product_code`（`m_routing_step.remark` の別名）, `source_bom_item_id`, `time_unit`, `lead_time_days`, `start_offset_min`, `duration_min`。
- 結合: `m_routing`（`routing_id`）、`m_product`（ルーティングの品番 `routing_product_*`・加工後品 `output_product_*`）、`m_process`、`m_line`、`m_supplier`。
- 非公開: `m_routing_step` の `step_type`・`created_at`・`updated_at`、`m_routing` の `description`・`created_at`・`updated_at`。
- 日付列なし（`date_field=None`＝全行）。

### 26.3 `v_ai_routing_step_material`（工程別部品消費。20列。`m_routing_step_material` を主とし、すべて主キーのLEFT JOIN。行数＝材料の行数）
`id`, `routing_step_id`, `routing_id`, `routing_code`, `routing_product_id`, `routing_product_code`, `routing_product_name`, `step_no`, `step_process_id`, `step_process_code`, `step_process_name`, `step_output_product_id`, `step_output_product_code`, `step_output_product_name`, `step_parent_product_code`（工程の `remark`）, `component_id`, `component_code`, `component_name`, `quantity`, `consume_timing`。
- 結合: `m_routing_step`→`m_routing`→`m_product`（ルーティングの品番）、`m_process`、`m_product`（加工後品・部品）。
- 非公開: `m_routing_step_material` の `remark`・`created_at`・`updated_at`。判断ページの公開列は5列（`id`・`routing_step_id`・`component_id`・`quantity`・`consume_timing`）。
- 日付列なし（全行）。

### 26.4 説明文に書くこと（確認できた事実のみ）
- `component_id` は消費する部品の品番ID（`m_product.id`）。`consume_timing` は START=工程開始、END=工程完了（モデルのラベル。開発DBの実値は START のみ。件数・値は説明に固定しない）。
- 使用個数（画面の項目）は、材料のビューの `quantity` から次の探し方で求められる値の一つで、**画面の使用個数と同じとは限らない**（BOSS承認 案A、2026-10-11）。ビューだけで求める方法（親品コードによる探し方）: 同じルーティング（`routing_id`）の中で、加工後品のコード（`output_product_code`）が、この工程の `parent_product_code` と等しい工程（親の工程。複数ありうる）の材料のうち、`component_id` が、この工程の `output_product_id` と等しい行の `quantity`（親の工程が複数、または同じ部品の行が複数あるときは合計が必要）。親の工程が見つからない、または該当する材料がない場合は、この方法では求められない。
- 画面は、階層パス（`hierarchy_path`）で見つけた親の工程の材料の合計を先に使い、求められないときに親品コードによる探し方、それでも求められないときにBOM明細の数量を使う（根拠: `RoutingMaster.vue` の `usageQuantity`、`masters/serializers.py:669-705`、`masters/admin.py:191-240`）。そのため、画面の使用個数と値が異なる場合がある。説明文には実データの件数・値・具体コードを書かない。
- 工程の数・工程の時間は `v_ai_routing_step` で集計する。材料のビューは材料の行ごとなので、工程の列（`step_no` など）が材料の数だけ繰り返される。**工程の数や時間を材料のビューで合計しない**（二重に数える）。
- 材料のない工程は、材料のビューに行がない（「その工程には登録された材料がない」）。調べるには、工程のビューの `id` が、材料のビューの `routing_step_id` にない行を探す。業務上の意味は未確認。
- `parent_product_code` は品番コードの文字列で、`v_ai_product.product_code` と結べる。ただし、品番マスタにない値が存在しうる（開発DBでは33工程。件数は説明に固定しない）。
- `step_type` は非公開（業務上の意味は未確認）。

### 26.5 基本ルールとの関係
- 結合はすべて、結合先の主キーでの LEFT JOIN（マスタ属性の付与のみ。行数不変）で、§4.1-2 の例外は不要。工程と材料は別々のビューにし、1対多の結合はしない。
- マイグレーション（標準SQL。`0042`・`0043`）、元テーブル `m_routing`・`m_routing_step`・`m_routing_step_material` の許可（置き換えず、ビューの追加のみ）、手順SQL（結合ビューのため手動。案A）は、実装済み（§26.8）。

### 26.6 BOSSに確認する点
1. 上の2ビュー・列でよいか。
2. 工程の `parent_product_code` に、品番マスタにない値（開発DBで33工程）があっても、そのまま出してよいか（空にはしない）。
3. 元テーブルの許可を、置き換えず、ビューの追加だけにしてよいか。

**BOSSの承認（2026-10-11）**：1＝はい（2ビュー・33列/20列）。2＝親品がマスタにない値は、そのまま出す（データはBOSSが後で調査・修正する。一覧は `output/routing_step_parent_not_in_product.csv`・`output/routing_step_parent_no_match_in_routing.csv`）。3＝はい（元テーブルの許可は置き換えず、ビューの追加のみ）。

### 26.7 手順SQL（`pm_ai_view_owner`への列権限と定義者の付け替え。MySQL固有のため手動。実行はBOSS。`<db>`は接続先のDB名。管理者で実行。`migrate ai 0042`・`0043` の後）
```sql
GRANT SELECT (`id`, `product_id`, `routing_code`, `is_default`, `is_active`, `valid_from_datetime`, `valid_to_datetime`) ON `<db>`.`m_routing` TO 'pm_ai_view_owner'@'localhost';
GRANT SELECT (`duration_min`, `hierarchy_depth`, `hierarchy_path`, `id`, `lead_time_days`, `line_id`, `output_product_id`, `parallel_count`, `parallel_group`, `process_id`, `remark`, `routing_id`, `source_bom_item_id`, `start_offset_min`, `step_no`, `supplier_id`, `time_unit`) ON `<db>`.`m_routing_step` TO 'pm_ai_view_owner'@'localhost';
GRANT SELECT (`id`, `routing_step_id`, `component_id`, `quantity`, `consume_timing`) ON `<db>`.`m_routing_step_material` TO 'pm_ai_view_owner'@'localhost';
-- m_product・m_process・m_line・m_supplier の id・コード・名称の列は、setup_ai_views --apply で付与済みの場合は不要(未付与なら先に実行)
CREATE OR REPLACE DEFINER = 'pm_ai_view_owner'@'localhost' SQL SECURITY DEFINER VIEW `<db>`.`v_ai_routing_step` AS
SELECT s.`id`, s.`routing_id`, r.`routing_code`, r.`product_id` AS `routing_product_id`, rp.`product_code` AS `routing_product_code`, rp.`product_name` AS `routing_product_name`,
       r.`is_default` AS `routing_is_default`, r.`is_active` AS `routing_is_active`, r.`valid_from_datetime` AS `routing_valid_from_datetime`, r.`valid_to_datetime` AS `routing_valid_to_datetime`,
       s.`step_no`, s.`parallel_group`, s.`parallel_count`, s.`hierarchy_depth`, s.`hierarchy_path`,
       s.`process_id`, pr.`process_code`, pr.`process_name`,
       s.`line_id`, l.`line_code`, l.`line_name`,
       s.`supplier_id`, sp.`supplier_code`, sp.`supplier_name`,
       s.`output_product_id`, op.`product_code` AS `output_product_code`, op.`product_name` AS `output_product_name`,
       s.`remark` AS `parent_product_code`, s.`source_bom_item_id`,
       s.`time_unit`, s.`lead_time_days`, s.`start_offset_min`, s.`duration_min`
FROM `<db>`.`m_routing_step` s
LEFT JOIN `<db>`.`m_routing` r ON r.`id` = s.`routing_id`
LEFT JOIN `<db>`.`m_product` rp ON rp.`id` = r.`product_id`
LEFT JOIN `<db>`.`m_process` pr ON pr.`id` = s.`process_id`
LEFT JOIN `<db>`.`m_line` l ON l.`id` = s.`line_id`
LEFT JOIN `<db>`.`m_supplier` sp ON sp.`id` = s.`supplier_id`
LEFT JOIN `<db>`.`m_product` op ON op.`id` = s.`output_product_id`;
CREATE OR REPLACE DEFINER = 'pm_ai_view_owner'@'localhost' SQL SECURITY DEFINER VIEW `<db>`.`v_ai_routing_step_material` AS
SELECT m.`id`, m.`routing_step_id`, s.`routing_id`, r.`routing_code`, r.`product_id` AS `routing_product_id`, rp.`product_code` AS `routing_product_code`, rp.`product_name` AS `routing_product_name`,
       s.`step_no`, s.`process_id` AS `step_process_id`, pr.`process_code` AS `step_process_code`, pr.`process_name` AS `step_process_name`,
       s.`output_product_id` AS `step_output_product_id`, op.`product_code` AS `step_output_product_code`, op.`product_name` AS `step_output_product_name`,
       s.`remark` AS `step_parent_product_code`,
       m.`component_id`, cp.`product_code` AS `component_code`, cp.`product_name` AS `component_name`, m.`quantity`, m.`consume_timing`
FROM `<db>`.`m_routing_step_material` m
LEFT JOIN `<db>`.`m_routing_step` s ON s.`id` = m.`routing_step_id`
LEFT JOIN `<db>`.`m_routing` r ON r.`id` = s.`routing_id`
LEFT JOIN `<db>`.`m_product` rp ON rp.`id` = r.`product_id`
LEFT JOIN `<db>`.`m_process` pr ON pr.`id` = s.`process_id`
LEFT JOIN `<db>`.`m_product` op ON op.`id` = s.`output_product_id`
LEFT JOIN `<db>`.`m_product` cp ON cp.`id` = m.`component_id`;
GRANT SELECT ON `<db>`.`v_ai_routing_step` TO 'pm_ai_reader'@'<readerのホスト部>';  -- 開発のreaderがDB全体のSELECTを持つ場合は不要
GRANT SELECT ON `<db>`.`v_ai_routing_step_material` TO 'pm_ai_reader'@'<readerのホスト部>';  -- 同上
```
手順SQLのビュー定義は、マイグレーション0042・0043のSELECT（標準SQL）と、列・結合・別名が同じであること。

### 26.8 実装記録（2026-10-11。generator。evaluator条件付き→指摘修正済み）
**変更ファイル**
- 新規 `pm_backend/apps/ai/migrations/0042_ai_routing_step_view.py`（`v_ai_routing_step`。標準SQL、`CREATE OR REPLACE VIEW`、逆は `DROP VIEW IF EXISTS`。依存は `ai 0041_ai_bom_item_view` と `masters 0086_add_is_order_day_to_calendar_day`＝列が揃う最新）。
- 新規 `pm_backend/apps/ai/migrations/0043_ai_routing_step_material_view.py`（`v_ai_routing_step_material`。依存は `ai 0042`・`masters 0086`）。
- `pm_backend/apps/ai/services/analysis_data_service.py`（`ANALYSIS_VIEWS` に2ビュー。label=ルーティング工程／ルーティング工程の材料、`date_field=None`・`quantity_field=None`、説明文）。
- `pm_backend/apps/ai/services/analysis_execution_service.py`（`ANALYSIS_COLUMN_TYPES` に33列・20列）。
- `pm_backend/apps/ai/services/sql_queries.py`（`BASE_SQL_SCHEMA` に2ビュー、`TABLE_NOTES` に2ビュー）。`m_routing` の既存3列・`SCREEN_SQL_TABLES`・`TERM_COLUMNS` は未変更。
- `pm_backend/apps/ai/management/commands/setup_ai_views.py`（`EXISTING_JOIN_VIEWS` に2ビュー、`OTHER_VIEW_COLUMNS` に `m_routing` 7列・`m_routing_step` 17列・`m_routing_step_material` 5列。コマンドの動作は未変更）。
- 試験: 新規 `test_analysis_routing_step_view.py`・`test_analysis_routing_step_material_view.py`、`test_setup_ai_views.py` に1件追加。
- 仕様書: 本節、`AI運用規約・AI用DB辞書.md` 6.5-12、`AI分析基盤仕様書.md`（ビュー一覧・列型の対応）。

**検証結果（generatorが実行した範囲。DB不要の試験のみ）**: `ai.test_analysis_routing_step_view`・`..._material_view`・`bom_item`・`calendar_day`・`customer`・`line`・`supplier`・`process`・`product`・`dateless`・`setup_ai_views`・`planning`・`column_guide`・`codegen`・`execution` の15モジュール、295件OK（skipped=4。SimpleTestCase系であることを確認。テスト用DBは作っていない）。`pm-ui/scripts/test-analysis-*.mjs` 7本 fail 0。`makemigrations --dry-run`＝No changes detected。既存7ビューの定義のSHA-256は `db31acbf…` のまま。

**evaluator（2026-10-11）の判定: 条件付き**。コード・型・行数・既存定義は合格。指摘は4点: ①開発DBに `migrate ai 0042`・`0043` が適用済み（2026-10-11 12:55:56。実行者不明）で、手順SQL（§26.7）は未実施だった。②使用個数の説明が、画面の探し方の一部のみだった。③試験が実データの混入（件数・具体コード・remarkの公開への反転など）を一部検出できなかった。④仕様書に未反映の記述があった。

**指摘への対応（generator。2026-10-11）**
- ①: 手順SQL（§26.7）をBOSS承認「はい」で実行済み（2026-10-11。GRANT 3文、`CREATE OR REPLACE DEFINER` 2文。定義者 `pm_ai_view_owner@localhost`・DEFINER を `information_schema` で確認。`setup_ai_views --check` の要対応0件、`ai_reader` 接続で2ビューが読める）。
- ②: 使用個数の説明を、「画面の使用個数と同じとは限らない」「ビューだけで求める方法（親品コードによる探し方）」「画面は階層パス→親品コード→BOM明細の順」と限定（`analysis_data_service.py` の `ANALYSIS_VIEWS`、`sql_queries.py` の `TABLE_NOTES`、本節 §26.1・§26.4、DB辞書 6.5-12、基盤仕様書）。SQL・列・マイグレーションは変えていない。
- ③: 2つのビューの試験の説明文チェックを強化（2桁以上の数字、件数の形、大文字の語は ID・DAY・MINUTE・START・END・BOM のみ許可、PURCHASE・OUTSOURCE・レーザ・FLOW・PARALLEL_POOL の禁止、材料のビューは「材料自身の remark は公開しない」の存在と「公開する」の禁止、「画面の使用個数と同じとは限らない」の存在）。説明文を書き換えた変異（33工程の追加、PURCHASE・G・レーザ1の追加、remark の公開への反転、「同じとは限らない」の削除）を、メモリ上の差し替えで流し、すべて失敗することを確認した。
- ④: 本節・DB辞書（6.5-12）・基盤仕様書（ビュー一覧・列型の対応）を現状に更新。

**検証結果（evaluatorの記録）**: DBなし295件OK（skipped=4）、フロント7本 fail 0、変異65通り、行数 工程7,678・材料6,421、全行型検査エラー0。`parent_product_code` がマスタにない値が33工程でそのまま出る。使用個数の内訳（説明文の方法）: 説明文どおりに計算できる6,364、画面と値が異なる30、階層パスのみ36、親の工程が複数167、親が見つからない38、親は見つかるが該当材料なし1,276。判断ページ（decisions）との照合は、検証環境では読めなかったが、呼び出し元（ArtifactData）の確認で、`m_routing` 7列・`m_routing_step` 17列・`m_routing_step_material` 5列の公開列が `OTHER_VIEW_COLUMNS` と一致した。`SHOW COLUMNS` との列型の照合は一致（2026-10-11）。

**未確認・未実施**: `pm_ai_reader` の列権限（開発の reader は DB 全体の SELECT を持つため確認不可）。DuckDBへの実投入。本番反映。修正後の再検証（evaluator）。

### 26.9 検証項目（DB上。反映後にevaluatorが読み取りで確認）
1. `v_ai_routing_step` の行数＝`m_routing_step` の行数（BOSS確認では7,678）。`v_ai_routing_step_material` の行数＝`m_routing_step_material` の行数（同6,421）。
2. 結合先の欠損（`routing_id` からの `m_routing`、`product_id` からの `m_product` など）の行数が、元のIDがあるのにマスタにない行の数と一致する。
3. `parent_product_code` が `v_ai_product.product_code` にない工程が、そのまま出ている（空にしていない。BOSS確認では33工程）。
4. `pm_ai_reader` の接続でビューが読め、非公開列（`step_type`・材料の `remark` など）は読めない。
5. 定義者が `pm_ai_view_owner@localhost`・DEFINER（`setup_ai_views --check` の要対応が0件）。
6. 全行×列が列型の検査を通る。`SHOW COLUMNS` が `ANALYSIS_COLUMN_TYPES` と一致する。
7. マイグレーションのSELECTと§26.7の手順SQLのSELECTが、列・結合・別名で同じ。

**反映状況（2026-10-11 更新）**：BOSS承認済み。コード実装済み（generator）。evaluator（2026-10-11）条件付き（指摘は §26.8 のとおり）→修正済み。**開発DB: `migrate ai 0042`・`0043` は適用済み、手順SQL（§26.7）はBOSS承認「はい」で実行済み**（定義者 `pm_ai_view_owner@localhost`・DEFINER、`setup_ai_views --check` 要対応0件、`ai_reader` 接続で2ビューが読める）。**本番未反映**。未確認: `pm_ai_reader` の列権限、DuckDB投入、修正後の再検証。コミット: 未（BOSSの指示待ち）。

## 27. ユーザー・部署のビュー `v_ai_user`・`v_ai_department` の実装記録（2026-10-11。BOSS承認済み。実装済み。evaluator条件付き合格（指摘は修正済み）。開発DBへ反映済み（migrate ai 0045/0046＋手順SQL）。本番未反映）

### 27.1 BOSSの回答（2026-10-11）
- 結合OK。プロフィール（`accounts_userprofile`）の結合キーは主キーの `user_id`（`p.user_id = u.id`）。部署のビューは組織の階層を表すため必要。ユーザーのビューには5つの所属（部署・事業部・係・班・グループ）の名称すべてを付ける。
- `level` の `division` は「事業部・課」と説明する（BOSS指定）。
- `WHERE u.username <> 'admin'`（admin アカウントを除外）を承認。説明文には「admin アカウントは含まれない」と書き、件数・値は固定しない。
- 公開しない列（判断ページ decisions の `auth_user` 6列・`accounts_userprofile` 11列・`accounts_department` 5列の公開列と一致させる）: `auth_user` の `password`・`last_login`・`is_superuser`・`email`・`date_joined`、`accounts_userprofile` の `created_at`・`updated_at`。ログインID（`username`）は外部AIへ送ってよい（BOSS決定）、社員コードは公開（BOSS決定）。
- `role`・`employment_type` の値の意味は、モデルのラベルのみ（コード・仕様書・権限仕様書で確認。権限仕様書に定義なし）。`employment_type` の `regular` は、モデルのラベルが「正準社員」（モデルの表記のまま書く）。「個人の評価に使わない」等の規定は書かない（BOSSが取り下げ済み）。懲戒判断をしない、は AI運用規約の既存規定に従う（既存の `v_ai_*` の説明には書いていない）。
- 追加指示（BOSS）: `role` は大事で、部署（組織）とつながっている。コードで確認できた次の事実を説明文・仕様書に記録する（推測と実データの件数・値は書かない）。
  1. 役割は所属する組織の階層に対応する: `manager`（事業部長・課長）＝事業部・課（`division_id`）、`chief`（係長）＝係（`group_id`）、`supervisor`（班長）＝班（`team_id`）、`leader`（リーダー）＝グループ（`unit_id`）。管理する部署は、その部署と配下の部署（`accounts_department.parent_id` をたどった子孫）。根拠: `pm_backend/apps/accounts/permission_scope.py`（`collect_managed_department_ids`）、`approval_views.py:66-73`、`role_utils.py`。
  2. 役割の序列（`role_utils.py` の `ROLE_RANK`）: `staff`・`office_staff`=0 < `leader`=1 < `supervisor`=2 < `chief`=3 < `manager`=4（`ROLE_RANK` にはこの他に `admin`=5 があるが、プロフィールの `role` の選択肢にはない）。
  3. 班長が複数の班を担当する `supervisor_teams`、リーダーが複数のグループを担当する `leader_units` という追加の担当割当（別テーブル）がある。ビューに含まないため、`team_id`・`unit_id` は「その人の所属」であり「担当するすべての班・グループ」ではない。
  - 実装上の注意（コードの読み取り）: `collect_managed_department_ids` は `leader` の管理部署を `leader_units` から集める（`profile.unit_id` は使わない）。一方、承認の対象者の絞り込み（`approval_views.py:66-73`、`role_utils.py`）は `unit_id` を使う。説明文は「役割とその階層のID列」の対応と「配下の部署」を書き、`v_ai_user` の説明文には、独立検証（2026-10-11）の指摘を受けて「管理する部署の集め方は役割ごとに異なる（コード上、リーダーの管理部署は、リーダーが担当するグループの割り当て（このビューには含まれない）から集められ、このビューの unit_id（所属）とは別である）。」の1文を追記した（根拠: `permission_scope.py:15-16`、`approval_views.py:66-67`、`role_utils.py`）。

### 27.2 `v_ai_user`（21列。`auth_user` を主とし、すべて主キーのLEFT JOIN。マイグレーション 0045）
`id`, `login_id`（`auth_user.username` の別名）, `first_name`, `last_name`, `is_active`, `is_staff`, `employee_code`, `employment_type`, `role`, `is_system_admin`, `joined_on`, `department_id`, `department_name`, `division_id`, `division_name`, `group_id`, `group_name`, `team_id`, `team_name`, `unit_id`, `unit_name`。
- 結合: `accounts_userprofile p ON p.user_id = u.id`、`accounts_department d1〜d5 ON d?.id = p.department_id / division_id / group_id / team_id / unit_id`。WHERE は `u.username <> 'admin'` のみ。
- 日付列なし（`joined_on` は入社日で期間の根拠にしない。`date_field=None`・`quantity_field=None`）。
- 依存: `ai 0044`、`accounts 0072`（最新）、`auth 0012`。

### 27.3 `v_ai_department`（6列。`accounts_department` の自己LEFT JOIN。マイグレーション 0046）
`id`, `name`, `level`, `display_id`, `parent_id`, `parent_name`（親の部署の `name`）。結合は `accounts_department pd ON pd.id = d.parent_id`（主キー）。WHEREなし（全行）。依存は `ai 0045`。`level` のモデルのラベル: `division`=事業部・課（BOSS指定。モデルのラベルは「事業部」）、`group`=係、`team`=班、`unit`=グループ。`parent_id` は親の部署のID、親が空の部署は親を持たない部署。`display_id` は表示順。ユーザーのビューの `department_id`・`division_id`・`group_id`・`team_id`・`unit_id` は `v_ai_department.id` と結べる。

### 27.4 機微な識別子の確認（コード調査）
- 分析パイプライン（`validate_datasets` など）は列を `BASE_SQL_SCHEMA` と照合するだけで、列名による拒否・マスクはない。`login_id`・`employee_code` は拒否されない。分析AIへ渡す前の名称→コードの置換（`analysis_redaction.build_analysis_code_redactor`）は、ユーザーの `username`・姓名を目的文の中で社員コードへ置換する（既存。変更なし）。
- 画面の読み取り専用SQL（`sql_queries._validate_sql`）の `SENSITIVE_IDENTIFIER` は `username` を含むが、`login_id`・`employee_code` は含まない。したがって `v_ai_user` 経由では拒否されない（元の列名 `username` は、ビューには存在しない）。
- 注意（BOSS判断の対象）: `SCREEN_SQL_TABLES['ai_home']` は `BASE_SQL_SCHEMA` の全ビューを含む。そのため `v_ai_user`（氏名・社員コード・ログインIDを含む）は、そのままではAIホームの読み取り専用SQLで、個人情報の権限を持たない利用者にも見える設計になる。これはBOSS判断（下の「決定」）により、`v_ai_user` をチャットの対象から外して対処した（`v_ai_user` 以外のビューは変更していない）。
- **決定（BOSS承認 案A。2026-10-11）**: `v_ai_user` は、AIホームのチャットSQLの対象から外した。`sql_queries.py` に `AI_HOME_EXCLUDED_TABLES = frozenset({'v_ai_user'})` を追加し、`SCREEN_SQL_TABLES['ai_home']` から差し引く（分析画面では `ai.analysis` の権限で使える。チャットの権限 `ai.chat` と分析の権限 `ai.analysis` は独立）。試験 `test_analysis_user_view.py` が、どの画面の対象にも含まれないことを固定する。**未コミット・開発DBへの影響なし（コードのみ）**。`v_ai_customer`（顧客名・略称）は、独立検証（2026-10-11）で、AIホームのチャットSQLに見えていることを確認した。**BOSS判断（2026-10-11）: 案B＝このまま見せる（チャットから外さない）**。

### 27.5 手順SQL（`pm_ai_view_owner` への列権限と定義者の付け替え。MySQL固有のため手動。実行はBOSS。`<db>` は接続先のDB名。管理者で実行。`migrate ai 0045`・`0046` の後。開発DBで実施済み 2026-10-11）
```sql
GRANT SELECT (`id`, `username`, `first_name`, `last_name`, `is_active`, `is_staff`) ON `<db>`.`auth_user` TO 'pm_ai_view_owner'@'localhost';
GRANT SELECT (`user_id`, `employee_code`, `employment_type`, `role`, `is_system_admin`, `joined_on`, `department_id`, `division_id`, `group_id`, `team_id`, `unit_id`) ON `<db>`.`accounts_userprofile` TO 'pm_ai_view_owner'@'localhost';
GRANT SELECT (`id`, `name`, `level`, `display_id`, `parent_id`) ON `<db>`.`accounts_department` TO 'pm_ai_view_owner'@'localhost';
CREATE OR REPLACE DEFINER = 'pm_ai_view_owner'@'localhost' SQL SECURITY DEFINER VIEW `<db>`.`v_ai_user` AS
SELECT u.`id`, u.`username` AS `login_id`, u.`first_name`, u.`last_name`, u.`is_active`, u.`is_staff`,
       p.`employee_code`, p.`employment_type`, p.`role`, p.`is_system_admin`, p.`joined_on`,
       p.`department_id`, d1.`name` AS `department_name`, p.`division_id`, d2.`name` AS `division_name`,
       p.`group_id`, d3.`name` AS `group_name`, p.`team_id`, d4.`name` AS `team_name`, p.`unit_id`, d5.`name` AS `unit_name`
FROM `<db>`.`auth_user` u
LEFT JOIN `<db>`.`accounts_userprofile` p ON p.`user_id` = u.`id`
LEFT JOIN `<db>`.`accounts_department` d1 ON d1.`id` = p.`department_id`
LEFT JOIN `<db>`.`accounts_department` d2 ON d2.`id` = p.`division_id`
LEFT JOIN `<db>`.`accounts_department` d3 ON d3.`id` = p.`group_id`
LEFT JOIN `<db>`.`accounts_department` d4 ON d4.`id` = p.`team_id`
LEFT JOIN `<db>`.`accounts_department` d5 ON d5.`id` = p.`unit_id`
WHERE u.`username` <> 'admin';
CREATE OR REPLACE DEFINER = 'pm_ai_view_owner'@'localhost' SQL SECURITY DEFINER VIEW `<db>`.`v_ai_department` AS
SELECT d.`id`, d.`name`, d.`level`, d.`display_id`, d.`parent_id`, pd.`name` AS `parent_name`
FROM `<db>`.`accounts_department` d
LEFT JOIN `<db>`.`accounts_department` pd ON pd.`id` = d.`parent_id`;
GRANT SELECT ON `<db>`.`v_ai_user` TO 'pm_ai_reader'@'<readerのホスト部>';  -- 開発のreaderがDB全体のSELECTを持つ場合は不要
GRANT SELECT ON `<db>`.`v_ai_department` TO 'pm_ai_reader'@'<readerのホスト部>';  -- 同上
```
手順SQLのビュー定義は、マイグレーション0045・0046のSELECT（標準SQL）と、列・結合・別名・WHEREが同じであること。

### 27.6 実装記録（2026-10-11。generator。evaluator未検証）
**変更ファイル**: 新規 `pm_backend/apps/ai/migrations/0045_ai_user_view.py`・`0046_ai_department_view.py`。`services/analysis_data_service.py`（`ANALYSIS_VIEWS` に2ビュー。label=ユーザー／部署）、`services/analysis_execution_service.py`（`ANALYSIS_COLUMN_TYPES`: int・bigint・tinyint(1)→BIGINT、varchar→VARCHAR、date→DATE）、`services/sql_queries.py`（`BASE_SQL_SCHEMA`・`TABLE_NOTES`。元テーブルの許可は未変更。`SCREEN_SQL_TABLES['ai_home']` から `AI_HOME_EXCLUDED_TABLES`（`v_ai_user`）を差し引く変更あり。他画面・`TERM_COLUMNS` は未変更）、`management/commands/setup_ai_views.py`（`EXISTING_JOIN_VIEWS` に2ビュー、`OTHER_VIEW_COLUMNS` に `auth_user` 6列・`accounts_userprofile` 11列・`accounts_department` 5列。コマンドの動作は未変更）。試験: 新規 `test_analysis_user_view.py`・`test_analysis_department_view.py`、`test_setup_ai_views.py` に1件追加。仕様書: 本節、`AI運用規約・AI用DB辞書.md` 6.5-13、`AI分析基盤仕様書.md`。
**generatorが実行した範囲（DB不要の試験のみ）**: 12モジュール（user・department・routing_step・routing_step_material・bom_item・calendar_day・dateless・setup_ai_views・planning・column_guide・codegen・execution）272件、失敗0・skipped=4（初回の2件の失敗は試験の書き方の誤りで修正。再実行で OK）。`pm-ui/scripts/test-analysis-*.mjs` 7本 fail 0。`makemigrations --dry-run`＝No changes detected。既存7ビューの定義のSHA-256は `db31acbf…` のまま。開発DBの読み取り: マイグレーションの SELECT をサブクエリで実行し、行数 ユーザー＝`auth_user` の件数−admin 除外分（開発DBで98件中1件を除外）、部署＝`accounts_department` の全行（行数一致）、列数 21・6 を確認（ビューは作っていない）。
**開発DBでの実施（2026-10-11）**: `migrate ai 0045`・`0046` をBOSSが実行（ai.0045_ai_user_view OK・ai.0046_ai_department_view OK）。手順SQL（§27.5。GRANT 3文＋CREATE OR REPLACE DEFINER 2文）を実行し、定義者 `pm_ai_view_owner@localhost`・DEFINER を `information_schema.VIEWS` で確認。`setup_ai_views --check` は要対応0件。`ai_reader` 接続で、`v_ai_user` 97件（元98件から admin を除く）・`v_ai_department` 39件が読め、`SHOW COLUMNS` の列名・順序が `ANALYSIS_COLUMN_TYPES` と一致（21列・6列）。`password`・`email`・`username`（v_ai_user）・`created_at`（v_ai_department）はビュー経由で読めない。`login_id` に `admin` はいない。

**未確認・未実施**: 判断ページ（decisions）との照合（検証担当の環境では読めなかった。呼び出し元の確認では列の一致を確認済み）、DuckDBへの実投入、本番反映、修正後の再検証（evaluator）。コミット: e644aae6（ユーザー・部署の実装）。

### 27.7 検証項目（反映後にevaluatorが読み取りで確認）
1. `v_ai_user` の行数＝`auth_user` の行数−`username='admin'` の行数。`v_ai_department` の行数＝`accounts_department` の行数。
2. `v_ai_user` に `admin` の行がない。非公開列（`password` など）が列にない。
3. 定義者が `pm_ai_view_owner@localhost`・DEFINER（`setup_ai_views --check` の要対応が0件）。`pm_ai_reader` の接続で2ビューが読める。
4. `SHOW COLUMNS` が `ANALYSIS_COLUMN_TYPES` と一致する。全行×列が列型の検査を通る。
5. マイグレーションのSELECTと§27.5の手順SQLが、列・結合・別名・WHEREで同じ。
6. `v_ai_user` がチャット（AIホーム）のSQLで拒否されること、分析では使えること（`ai.analysis` の権限）。`v_ai_department` はチャットで使え、チャットのSQL辞書（`TABLE_NOTES`）の文面に `v_ai_user` の名前が出ないこと。

**反映状況（2026-10-11）**：BOSS承認済み。コード実装済み（generator）。evaluator未検証。**開発DB: `migrate ai 0045`・`0046`、手順SQL（§27.5）とも実施済み。本番未反映**。

### 27.8 今後の候補・保留
班長（supervisor）が複数の班を担当する割り当て（accounts_userprofile_supervisor_teams。モデル UserProfile.supervisor_teams）と、リーダー（leader）が複数のグループを担当する割り当て（accounts_userprofile_leader_units。UserProfile.leader_units）は、今回の v_ai_user には含めない。担当の割り当てもビューにしたい場合は、別のビューとして作る。その場合、判断ページ（decisions）で、これらのテーブルの公開列をBOSSが決める（未決定のため、現在は非公開として扱う）。
**更新（2026-10-11）**: 上の保留は、§29 で実装した（別ビュー `v_ai_supervisor_team`・`v_ai_leader_unit`。公開列はBOSS承認）。

## 28. グループとラインの紐付のビュー `v_ai_unit_line` の実装記録（2026-10-11。BOSS承認済み。実装済み。evaluator合格（2026-10-11）。開発DBへ反映済み（`migrate ai 0048`＋手順SQL）。本番未反映）

### 28.1 BOSSの回答（2026-10-11）
- 判断ページ（decisions）に `accounts_unit_line_mapping` の記載がなかったため、提案した公開列5列（`id`・`unit_id`・`line_id`・`sort_order`・`is_default`）を承認。
- 結合で付ける名前（`accounts_department.name`→`unit_name`、`m_line.line_code`・`line_name`）を承認。これらは既存の `v_ai_department`（`name`）・`v_ai_line`（`line_code`・`line_name`）の公開列に含まれる。
- 説明は確認できた範囲のみ書く（未確認は「未確認」）。実データの件数・値・具体的なグループ名・ライン名は書かない。
- チャット（AIホーム）のSQLには見せてよい（個人情報を含まない）。`AI_HOME_EXCLUDED_TABLES` には入れない。

### 28.2 `v_ai_unit_line`（8列。`accounts_unit_line_mapping` を主とし、すべて主キーのLEFT JOIN。マイグレーション 0048）
`id`, `unit_id`, `unit_name`（`accounts_department.name`）, `line_id`, `line_code`, `line_name`（`m_line`）, `sort_order`, `is_default`。
- 結合: `accounts_department u ON u.id = m.unit_id`、`m_line l ON l.id = m.line_id`（いずれも相手の主キー。行数は `accounts_unit_line_mapping` と同じ）。WHEREなし（全行）。`date_field=None`・`quantity_field=None`（label=グループのライン）。
- 非公開（ビューに含めない）: `created_at`・`updated_at`。
- 列型（開発DBの `SHOW COLUMNS` から導出）: bigint→BIGINT（`id`・`unit_id`・`line_id`）、varchar→VARCHAR（`unit_name`・`line_code`・`line_name`）、int→BIGINT（`sort_order`）、tinyint(1)→BIGINT（`is_default`）。ビュー作成後の `SHOW COLUMNS` との照合は、開発DBで実施済みで一致した（2026-10-11）。
- 依存: `ai 0047_aianalysisrun_purpose`（下の「マイグレーション番号」を参照）。

### 28.3 説明文に書いた事実（コードで確認。推測は書かない）
- 1行＝1つの「グループとラインの紐付」。グループは部署の階層 `unit` のグループ（モデル `UnitLineMapping.unit` は `limit_choices_to={'level': 'unit'}`）。`unit_id` は `v_ai_department.id`、`line_id` は `v_ai_line.id` と結べる。モデルのラベル: `sort_order`＝表示順、`is_default`＝初期ライン。
- ユーザー（プロフィール）の所属グループ（`v_ai_user.unit_id`）に対応する紐付が、そのユーザーが使うラインの一覧として、`is_default` の降順、`sort_order` の昇順、`id` の順に返される（根拠: `pm_backend/apps/accounts/serializers.py` の `get_unit_lines`。管理画面のAPIは `api_views.py` の `UnitLineMappingViewSet`）。
- 同じグループ・同じラインの組は一意（`unique_together`）。同じラインを複数のグループが、1つのグループが複数のラインを紐付けられる（モデル上、多対多の紐付）。
- **未確認**: `is_default` の運用、画面でのラインの絞り込みなど業務上の意味（説明文にも「未確認」と書いた）。
- チャットの辞書（`TABLE_NOTES`）の文面には `v_ai_user` の名前を出さない（「プロフィールの `unit_id`」と書く。`v_ai_user` はチャットから除外されているため）。分析側の説明（`ANALYSIS_VIEWS`）は `v_ai_user` と結べることを書く。

### 28.4 マイグレーション番号
指示は `0047_ai_unit_line_view.py`（依存 `ai 0046`）だったが、別の作業が `0047_aianalysisrun_purpose.py`（依存 `ai 0046`・未コミット）を追加済みだったため、同じ 0046 から2本に分岐すると migrate が「Conflicting migrations」で止まる。そこで `0048_ai_unit_line_view.py` とし、依存を `('ai', '0047_aianalysisrun_purpose')` にした。`makemigrations --dry-run` は No changes detected。**BOSS確認事項**: `0047_aianalysisrun_purpose` が先にコミット・適用されること（または番号の付け替え）。

### 28.5 手順SQL（`pm_ai_view_owner` への列権限と定義者の付け替え。MySQL固有のため手動。実行はBOSS。`<db>` は接続先のDB名。管理者で実行。`migrate ai 0048` の後）
```sql
GRANT SELECT (`id`, `unit_id`, `line_id`, `sort_order`, `is_default`) ON `<db>`.`accounts_unit_line_mapping` TO 'pm_ai_view_owner'@'localhost';
CREATE OR REPLACE DEFINER = 'pm_ai_view_owner'@'localhost' SQL SECURITY DEFINER VIEW `<db>`.`v_ai_unit_line` AS
SELECT m.`id`, m.`unit_id`, u.`name` AS `unit_name`, m.`line_id`, l.`line_code`, l.`line_name`, m.`sort_order`, m.`is_default`
FROM `<db>`.`accounts_unit_line_mapping` m
LEFT JOIN `<db>`.`accounts_department` u ON u.`id` = m.`unit_id`
LEFT JOIN `<db>`.`m_line` l ON l.`id` = m.`line_id`;
GRANT SELECT ON `<db>`.`v_ai_unit_line` TO 'pm_ai_reader'@'<readerのホスト部>';  -- 開発のreaderがDB全体のSELECTを持つ場合は不要
```
- `accounts_department` の `name`（§27.5 の GRANT に含む）、`m_line` の `line_code`・`line_name`（`v_ai_line` の公開列。`setup_ai_views --apply` で付与済み）は既存の付与で足りる。`m_line` の GRANT は不要。念のため、実行前に次で確認する（管理者）: `SHOW GRANTS FOR 'pm_ai_view_owner'@'localhost';` に `accounts_department` の `name`、`m_line` の `line_code`・`line_name` の列権限があること。足りなければ次を追加する。
```sql
GRANT SELECT (`name`) ON `<db>`.`accounts_department` TO 'pm_ai_view_owner'@'localhost';
GRANT SELECT (`id`, `line_code`, `line_name`) ON `<db>`.`m_line` TO 'pm_ai_view_owner'@'localhost';
```
- 手順SQLのビュー定義は、マイグレーション0048のSELECT（標準SQL）と、列・結合・別名・WHEREが同じであること。

### 28.6 実装記録（2026-10-11。generator。evaluator未検証）
**変更ファイル**: 新規 `pm_backend/apps/ai/migrations/0048_ai_unit_line_view.py`。`services/analysis_data_service.py`（`ANALYSIS_VIEWS` に1ビュー）、`services/analysis_execution_service.py`（`ANALYSIS_COLUMN_TYPES`）、`services/sql_queries.py`（`BASE_SQL_SCHEMA`・`TABLE_NOTES`。元テーブルの許可・画面SQLは置き換えず、`AI_HOME_EXCLUDED_TABLES` は未変更）、`management/commands/setup_ai_views.py`（`EXISTING_JOIN_VIEWS` に追加、`OTHER_VIEW_COLUMNS` に `accounts_unit_line_mapping` の5列。コマンドの動作は未変更）。試験: 新規 `test_analysis_unit_line_view.py`、`test_setup_ai_views.py` を更新。仕様書: 本節、`AI運用規約・AI用DB辞書.md` 6.5-14、`AI分析基盤仕様書.md`（ビュー一覧・列型の対応）。
**generatorが実行した範囲**: DB不要の試験 9モジュール 172件（unit_line・user・department・routing_step・dateless・setup_ai_views・planning・column_guide・execution）。失敗1件は `ai.test_analysis_execution.TimingTest.test_transfer_time_excludes_launcher_execution_and_response_wait`（転送時間 1.088秒 < 1.0秒 の時間依存の試験）で、今回の変更とは無関係（単独で再実行して OK）。`pm-ui/scripts/test-analysis-*.mjs` 7本 exit 0。既存7ビューの定義のSHA-256は `db31acbf…` のまま。開発DBの読み取り: マイグレーションのSELECTをサブクエリで実行し、行数＝`accounts_unit_line_mapping` の行数（一致）、結合先の欠け（`unit_name`・`line_code` がNULL）0件、列名・順序が公開8列と一致を確認（ビューは作っていない。`information_schema.VIEWS` に `v_ai_unit_line` はない）。

### 28.7 検証項目（反映後にevaluatorが読み取りで確認）
1. `v_ai_unit_line` の行数＝`accounts_unit_line_mapping` の行数。`SHOW COLUMNS` が `ANALYSIS_COLUMN_TYPES`（8列）と一致する。`created_at`・`updated_at` が読めない。
2. 定義者が `pm_ai_view_owner@localhost`・DEFINER（`setup_ai_views --check` の要対応が0件）。`pm_ai_reader` の接続で読める。
3. マイグレーション0048のSELECTと §28.5 の手順SQLが、列・結合・別名・WHEREで同じ。
4. チャット（AIホーム）のSQLと辞書にこのビューが出ること、`TABLE_NOTES` に `v_ai_user` の名前が出ないこと。
5. 説明文に件数・グループ名・ライン名が入っていないこと。

**反映状況（2026-10-11）**：BOSS承認済み。コード実装済み（generator）。evaluator未検証。**開発DB: `migrate ai 0048`（BOSSが適用）・手順SQL（§28.5。GRANT 1文＋CREATE OR REPLACE DEFINER 1文）とも実施済み（2026-10-11）。定義者 `pm_ai_view_owner@localhost`・DEFINER、`setup_ai_views --check` 要対応0件、`ai_reader` 接続で28件・列名と順序が `ANALYSIS_COLUMN_TYPES` と一致（8列）・結合先欠損0件・ビュー経由では `created_at` は読めない（開発の `pm_ai_reader` は DB 全体の SELECT を持つため、元テーブルは物理的に読める。本番の権限設計は別途確認）。本番未反映**。コミット: 2ae99342。独立検証（evaluator。2026-10-11）: 合格。DBなしの試験270件OK・変異試験で検出、開発DB（読み取り）で28行・欠損0・重複0・全行の型検査エラー0・グループは全て level=unit・多対多が実データでも成立。軽微: 日本語の具体名の混入は機械で検出できない。

## 29. 班長の担当班・リーダーの担当グループのビュー `v_ai_supervisor_team`・`v_ai_leader_unit` の実装記録（2026-10-11。BOSS承認済み。コード実装済み。evaluator条件付き合格（指摘は本更新で対応）。開発DBへ反映済み（`migrate ai 0049`・`0050`＋手順SQL §29.5）。本番未反映）

### 29.1 BOSSの回答（2026-10-11）
- 「このビューは大事ではない。適当に作って」＝公開列は最小構成（呼び出し元が決定）。その後、「氏名や社員コードを付けてもいい」で、ユーザーの識別情報（ログインID・姓・名・社員コード）を主キーLEFT JOINで追加。さらに「1a」で、この案（A）を再度選んだ。
- 説明は確認できた範囲のみ書く（未確認は「未確認」）。実データの件数・値・氏名・部署名は書かない。

### 29.2 列（各8列。中間テーブルを主とし、すべて主キーのLEFT JOIN。WHEREなし）
| ビュー（マイグレーション） | 元テーブル | 列（この順） |
|---|---|---|
| `v_ai_supervisor_team`（0049。依存 `ai 0048`） | `accounts_userprofile_supervisor_teams` m | `m.id`, `m.userprofile_id AS user_id`, `a.username AS login_id`, `a.last_name`, `a.first_name`, `p.employee_code`, `m.department_id AS team_id`, `d.name AS team_name` |
| `v_ai_leader_unit`（0050。依存 0049） | `accounts_userprofile_leader_units` m | 上と同じ。ただし `m.department_id AS unit_id`, `d.name AS unit_name` |
- 結合: `auth_user a ON a.id = m.userprofile_id`、`accounts_userprofile p ON p.user_id = m.userprofile_id`、`accounts_department d ON d.id = m.department_id`（いずれも相手の主キー。行数は中間テーブルと同じ）。`date_field=None`・`quantity_field=None`（label=班長の担当班／リーダーの担当グループ）。
- 非公開（ビューに含めない）: `auth_user` の `password`・`email` 等、`accounts_userprofile` の `employee_code` 以外の列。中間テーブルに他の列はない。
- 列型（開発DBの `SHOW COLUMNS` から導出）: 中間テーブル id=bigint・userprofile_id=int・department_id=bigint→BIGINT、`auth_user` の username・first_name・last_name=varchar(150)、`employee_code`=varchar(32)、`name`=varchar→VARCHAR。ビュー作成後の列名・順序・型の照合は、開発DBで実施済みで一致した（2026-10-11）。
- admin アカウントの除外はしない（中間テーブルの行は、担当者が admin でも含みうる。`v_ai_user` は admin を除くため、結合できない行がありうる）。開発DBの読み取りでは、admin の行・auth_user／プロフィール／部署に結べない行はどちらのビューも0件だった（件数そのものは説明文に書かない）。

### 29.3 チャット（AIホーム）への出し方（呼び出し元の判断。BOSSは「氏名・社員コードを付けてもよい」と承認。`v_ai_user` をチャットから外す案Aと同じ方針）
氏名・社員コード・ログインIDを含むため、`AI_HOME_EXCLUDED_TABLES` に2ビューを追加し、チャットのSQLと辞書に出さない（`v_ai_user` と同じ方針。BOSS承認 案A）。分析では `ai.analysis` の権限で使える。「個人情報の権限で絞られないチャットでは、氏名等を持つビューを出さない」判断に合わせた。これは氏名等を付ける案を選んだ場合の必須条件である。

### 29.4 説明文に書いた事実（コードで確認。推測は書かない）
- `v_ai_supervisor_team`: 1行＝「班長（role=supervisor）が追加で担当する班」の割り当て1つ（モデルのラベル「班長担当班」。`UserProfile.supervisor_teams`・`limit_choices_to` level=team）。`team_id` は `v_ai_user.team_id`（所属）とは別。コード上、班長の管理部署は所属の班と担当班を合わせて配下を含めて集められる（`accounts/permission_scope.py` の `collect_managed_department_ids`）。
- `v_ai_leader_unit`: 1行＝「リーダー（role=leader）が担当するグループ」の割り当て1つ（モデルのラベル「リーダー担当グループ」。`UserProfile.leader_units`・level=unit）。コード上、リーダーの管理部署は担当グループ（`unit_id`）から集められる（所属の `v_ai_user.unit_id` ではない）。
- 両ビュー: `user_id` は `v_ai_user.id`、`team_id`／`unit_id` は `v_ai_department.id` と結べる。`login_id`・氏名・社員コードは `v_ai_user` と同じ値。1ユーザーが複数の行を持ちうる（多対多）。
- **未確認**: 業務上の運用（追加担当の意味、承認ルートとの関係）。

### 29.5 手順SQL（`pm_ai_view_owner` への列権限と定義者の付け替え。MySQL固有のため手動。実行はBOSS。`<db>` は接続先のDB名。管理者で実行。`migrate ai 0049`・`0050` の後）
```sql
GRANT SELECT (`id`, `userprofile_id`, `department_id`) ON `<db>`.`accounts_userprofile_supervisor_teams` TO 'pm_ai_view_owner'@'localhost';
GRANT SELECT (`id`, `userprofile_id`, `department_id`) ON `<db>`.`accounts_userprofile_leader_units` TO 'pm_ai_view_owner'@'localhost';
CREATE OR REPLACE DEFINER = 'pm_ai_view_owner'@'localhost' SQL SECURITY DEFINER VIEW `<db>`.`v_ai_supervisor_team` AS
SELECT m.`id`, m.`userprofile_id` AS `user_id`, a.`username` AS `login_id`, a.`last_name`, a.`first_name`, p.`employee_code`, m.`department_id` AS `team_id`, d.`name` AS `team_name`
FROM `<db>`.`accounts_userprofile_supervisor_teams` m
LEFT JOIN `<db>`.`auth_user` a ON a.`id` = m.`userprofile_id`
LEFT JOIN `<db>`.`accounts_userprofile` p ON p.`user_id` = m.`userprofile_id`
LEFT JOIN `<db>`.`accounts_department` d ON d.`id` = m.`department_id`;
CREATE OR REPLACE DEFINER = 'pm_ai_view_owner'@'localhost' SQL SECURITY DEFINER VIEW `<db>`.`v_ai_leader_unit` AS
SELECT m.`id`, m.`userprofile_id` AS `user_id`, a.`username` AS `login_id`, a.`last_name`, a.`first_name`, p.`employee_code`, m.`department_id` AS `unit_id`, d.`name` AS `unit_name`
FROM `<db>`.`accounts_userprofile_leader_units` m
LEFT JOIN `<db>`.`auth_user` a ON a.`id` = m.`userprofile_id`
LEFT JOIN `<db>`.`accounts_userprofile` p ON p.`user_id` = m.`userprofile_id`
LEFT JOIN `<db>`.`accounts_department` d ON d.`id` = m.`department_id`;
GRANT SELECT ON `<db>`.`v_ai_supervisor_team` TO 'pm_ai_reader'@'<readerのホスト部>';  -- 開発のreaderがDB全体のSELECTを持つ場合は不要
GRANT SELECT ON `<db>`.`v_ai_leader_unit` TO 'pm_ai_reader'@'<readerのホスト部>';  -- 同上
```
- `auth_user`（`id`・`username`・`first_name`・`last_name`）、`accounts_userprofile`（`user_id`・`employee_code`）、`accounts_department`（`id`・`name`）は、§27.5 の GRANT（`v_ai_user`・`v_ai_department` 用）に含まれるため、追加は不要。念のため実行前に `SHOW GRANTS FOR 'pm_ai_view_owner'@'localhost';` で、これらの列権限があることを確認する。
- 手順SQLのビュー定義は、マイグレーション0049・0050のSELECT（標準SQL）と、列・結合・別名・WHEREが同じであること。

### 29.6 実装記録（2026-10-11。generator。evaluator未検証）
**変更ファイル**: 新規 `pm_backend/apps/ai/migrations/0049_ai_supervisor_team_view.py`・`0050_ai_leader_unit_view.py`。`services/analysis_data_service.py`（`ANALYSIS_VIEWS` に2ビュー）、`services/analysis_execution_service.py`（`ANALYSIS_COLUMN_TYPES`）、`services/sql_queries.py`（`BASE_SQL_SCHEMA`・`TABLE_NOTES`・`AI_HOME_EXCLUDED_TABLES` に2ビューを追加）、`management/commands/setup_ai_views.py`（`EXISTING_JOIN_VIEWS` に追加、`OTHER_VIEW_COLUMNS` に中間テーブル各3列。コマンドの動作は未変更）。試験: 新規 `test_analysis_supervisor_team_view.py`・`test_analysis_leader_unit_view.py`、`test_setup_ai_views.py` を更新。仕様書: 本節、§27.8、`AI運用規約・AI用DB辞書.md` 6.5-15、`AI分析基盤仕様書.md`（ビュー一覧・列型の対応）。
**反映状況（2026-10-11）**：コミット済み（315d4849）。**開発DB: `migrate ai 0049`・`0050`（BOSSが適用）・手順SQL（§29.5。GRANT 2文＋CREATE OR REPLACE DEFINER 2文）とも実施済み**。定義者 `pm_ai_view_owner@localhost`・DEFINER、`setup_ai_views --check` 要対応0件。**evaluator（2026-10-11）: 条件付き合格**（コード・開発DBは合格、条件は仕様書の記述が古いこと→本更新で対応）。DBなしの試験300件OK、変異約55通りを検出（日本語の氏名の混入だけ機械では検出できない）、画面の試験7本OK。開発DB（読み取り）: 班長5行・リーダー9行＝中間テーブルと同じ、全行×8列の型検査エラー0、結合先欠損0、admin の行0、`v_ai_user` に無い user_id 0、team_id は全て level=team・unit_id は全て level=unit、割り当てを持つユーザーの role は班長ビューが全て supervisor・リーダービューが全て leader（参考: role=leader のユーザーの一部は割り当てなし）。チャットSQLで2ビューが拒否されることを実呼び出しで確認。本番未反映。

### 29.7 検証項目（反映後にevaluatorが読み取りで確認）
1. 各ビューの行数＝中間テーブルの行数。`SHOW COLUMNS` が `ANALYSIS_COLUMN_TYPES`（8列）と一致する。`password`・`email` が読めない。
2. 定義者が `pm_ai_view_owner@localhost`・DEFINER（`setup_ai_views --check` の要対応が0件）。
3. マイグレーションのSELECTと §29.5 の手順SQLが、列・結合・別名・WHEREで同じ。
4. チャット（AIホーム）のSQLと辞書に2ビューが出ないこと、分析（`ANALYSIS_VIEWS`）では使えること。
5. 説明文に件数・氏名・部署名・社員コードが入っていないこと。

## 30. 説明文の改善: 工程とBOM明細の結びつきと連産品の判定規則（2026-10-11。BOSS承認「はい」。判定規則は加工後品ベースに訂正済み（BOSS承認「はい」×3）。コードのみ・DB変更なし。evaluator未検証）

対象: `v_ai_routing_step`・`v_ai_routing_step_material`・`v_ai_bom_item` の説明文（`analysis_data_service.py` の `ANALYSIS_VIEWS`、`sql_queries.py` の `TABLE_NOTES`）。ビューのSQL・列・マイグレーションは変えていない。

### 30.1 原因
分析AIが「連産品の代表でない子の工程を除外して、所要時間を一覧にする」分析で、179工程すべてを unknown にした。AIに渡る情報は説明文だけ（AIは仕様書を読まない）で、(1) 工程とBOM明細の結びつけ方、(2) 連産品・代表品の判定規則、が書かれていなかった。

### 30.2 追記した事実と出典（実データの件数・具体コードは説明文に書かない）
1. 結びつき: `v_ai_routing_step.source_bom_item_id` は、工程の元になったBOM明細のIDで、`v_ai_bom_item.id` と結べる。空の工程は元のBOM明細が不明（結べない）。出典: `masters/models.py` の `RoutingStep.source_bom_item`（ForeignKey(BOMItem)、verbose_name「元BOM明細」）。`v_ai_routing_step_material` は `routing_step_id` で工程ビューの `id` と結べる（既存の記述。工程の元BOM明細・連産品の判定は工程ビューの列で行う旨を追記）。
2. 連産品: 1つの工程で複数の製品が同時に生産されるもの。BOMでは親が仮想セット品番（`m_product.is_virtual_set`。在庫を持たない）、子が実際に同時にできる複数の品番。BOMヘッダに連産品BOMのフラグ（`bom_is_coproduct`。親が仮想セット品番のときは自動で1）。通常のBOMとは逆方向の関係（仮想セット品番から子へ展開）のため、在庫の出庫計算・受注展開では除外される。出典: `masters/models.py` `BOM.is_coproduct` の help_text、`MASTER_TABLES_DEFINITION.MD` 9章、在庫計算仕様書、受注展開仕様書、`masters/serializers.py`。
3. 代表品: 連産品BOMの子のうち1つに指定する（`is_coproduct_driver`）。計画展開の起点で、代表品の所要時間（`duration_min`）が連産品のサイクルタイムとして使われる。「代表でない子」＝連産品BOMの子で、代表品に指定されていないもの。出典: `MASTER_TABLES_DEFINITION.MD` 9章、単独計画仕様書「サイクルタイム解決」。

### 30.3 判定の考え方（BOSS承認 2026-10-11「はい」。加工後品ベース。初版の「元のBOM明細ベース」を訂正）
工程が連産品に関わるかは、**工程の加工後品（`v_ai_routing_step.output_product_code`）**で判定する。`v_ai_bom_item` の `bom_is_coproduct=1` の明細の `child_product_code` に、工程の `output_product_code` が含まれるかで見る。システム本体（ルーティング画面）の代表部品の表示は、元のBOM明細がない工程についてだけこの規則と同じである（`masters/serializers.py` の `RoutingStepSerializer.get_representative_part`、`masters/views.py` の `_get_coproduct_driver_child_ids`・`_build_representative_child_ids`: 元のBOM明細があればその `is_coproduct_driver` だけを見て加工後品では判定しない。なければ、工程の `output_product_id` が「連産品BOM（`bom__is_coproduct=True`）で `is_coproduct_driver=True` の明細の `child_product_id` の集合」に含まれるかで見る）。食い違いは §30.4。
- その品番が、`bom_is_coproduct=1` の明細のどれかで `is_coproduct_driver=1` ＝連産品の代表の工程（残す）。同じ品番が代表としても代表でない子としても登録されている場合も、代表として扱う（BOSS承認）。
- `bom_is_coproduct=1` の明細にだけ（すべて `is_coproduct_driver=0`）子として登録されている ＝連産品の代表でない子の工程（除外の対象）。
- `bom_is_coproduct=1` の明細の子として登録されていない ＝通常の工程。
- 判定できない（不明）のは、加工後品（`output_product_code`）が空の工程だけ。加工後品があって連産品の子として登録されていない工程を不明にしない。
- 結ぶときの注意: `v_ai_bom_item` は同じ子品番が複数の明細に現れうるので、先に `bom_is_coproduct=1` の明細を `child_product_code` で集約（`GROUP BY child_product_code`、`MAX(is_coproduct_driver)`）してから工程に結ぶ。明細の行ごとに結ぶと工程の行が重複して増える。
- `source_bom_item_id`（元のBOM明細）は、連産品の判定には使わない。説明文には、事実として「ルーティング画面の代表部品の表示は、元のBOM明細があるときはその明細の代表品フラグを見るため、ここでの判定（工程の加工後品で見る）と異なる場合がある」とだけ書く（実データの件数は書かない。2026-10-12に訂正。旧文言「システム本体も…連産品の子の工程は加工後品で判定する」は誤り）。
- 工程を残すには、集約結果へ外部結合で結ぶ。内部結合にすると連産品でない通常の工程が消える旨を、説明文に1文足した（2026-10-12）。
- 説明文では `GROUP BY`・`MAX` の大文字語を避け、「`child_product_code` でグループ化し、`is_coproduct_driver` の最大値に集約する」と書く（`check_no_fixed_values` の許可語を増やさないため）。

### 30.4 実データでの確認と、初版の規則が成り立たなかった経緯（開発DB。件数は説明文には書かない）
初版（コミット bc412a7e）の規則「工程の元のBOM明細（`source_bom_item_id` で `v_ai_bom_item.id` と結ぶ）が `bom_is_coproduct=1` かつ `is_coproduct_driver=0` なら、連産品の代表でない子に由来する工程」は、独立検証（evaluator）と呼び出し元の確認で、実データで一度も成り立たないことが分かった。
- 連産品BOMの明細を元のBOM明細として持つ工程: 0件。`source_bom_item_id` がある6073工程は、すべて通常のBOMの明細を指す。
- 初版の §30.4（品番 YD40006245 の `source_bom_item_id` がある178件はすべて `bom_is_coproduct=0` なので「通常の工程と判定できる」）の結論は誤り。これらは通常のBOMの明細を指しているだけで、連産品の子かどうかは加工後品で見る必要がある。
- 加工後品が連産品BOMの子として登録されている工程: 807件（代表として登録されている品番のもの164、代表でない子のみのもの643）。
- 品番 YD40006245: 179工程中27工程（代表5・代表でない子22）。
- 同じ品番が代表としても代表でない子としても登録されているものが2品番（BOSS承認「代表として扱う」）。
- 新しい規則での再確認（generator、開発DB・ai_reader・SELECTのみ、2026-10-11）: 全工程7678件 = 通常6871 + 代表164 + 代表でない子643 + 不明0（加工後品が空の工程は0件）。YD40006245（`routing_product_code`）は 179 = 通常152 + 代表5 + 代表でない子22 + 不明0。`bom_is_coproduct=1` の明細を `child_product_code` ごとに `MAX(is_coproduct_driver)` へ集約して結んだ結果の合計が工程の行数（179、全体7678）と一致し、結合で行は増えない。

#### 30.4-2 ルーティング画面（システム本体）との食い違い（独立検証の指摘。開発DB。2026-10-12）
- 元のBOM明細がない1605工程: 説明文の規則と画面は一致（代表12・代表でない子45・通常1548）。
- 元のBOM明細がある6073工程: 画面は元のBOM明細の `is_coproduct_driver` だけを見る。その明細は全件 `is_coproduct_driver=0` のため、画面は全件「代表でない」と表示する。
- 説明文の規則（加工後品で判定）との食い違い: 152工程（品番77・ルーティング41）。説明文の規則では代表、画面では代表でない。YD40006245 の代表5工程はこの152工程に含まれる（元のBOM明細があり、その明細は driver=0。加工後品は代表として登録）。
- 逆の食い違い（画面で代表、説明文の規則で代表でない）: 0件。
- 同じ品番が代表としても代表でない子としても登録されているもの2品番（3工程。3工程とも元のBOM明細あり）: 説明文の規則では代表として扱う。「システム本体と同じ」は、元のBOM明細がない工程についてだけ正しい。
- BOSS判断（2026-10-12「直して」）: 説明文の規則（加工後品ベース）を維持する。BOSSの目的（連産品は代表品のみ表示）に合い、BOSSが確認した5工程と一致するため。画面の代表部品の表示の食い違いは別件で、今回は手を付けない（元のBOM明細の代表品フラグが実データで常に0のため、画面の不具合の可能性がある）。
- 説明文の訂正: 「システム本体も…加工後品で判定する」を、「画面の代表部品の表示は元のBOM明細の代表品フラグを見るため、ここでの判定と異なる場合がある」に直した。

### 30.5 変更内容
- `analysis_data_service.py` / `sql_queries.py`: 工程ビューの `source_bom_item_id` の説明を確定（「未確認」の列挙から除外）し、連産品・代表品・判定規則を追記。BOM明細ビューの `bom_is_coproduct`・`is_coproduct_driver` の説明を詳しくし、工程ビューとの結びつきを追記。材料ビューに連産品の判定の結び方を追記。
- 訂正（コミット bc412a7e の後）: 判定規則を元のBOM明細ベースから加工後品ベースに改め（§30.3）、`source_bom_item_id` は判定に使わない旨、集約の注意（`child_product_code` でグループ化し `is_coproduct_driver` の最大値）、不明は加工後品が空の工程だけ、を説明文（`ANALYSIS_VIEWS`・`TABLE_NOTES` の同内容2か所）に反映。材料ビューは「`routing_step_id` で工程ビューと結び、工程ビューの `output_product_code` と `v_ai_bom_item` で判定」に直した。
- 試験: `test_analysis_routing_step_view.py`（`test_description_has_bom_item_link_and_coproduct_rule` を加工後ベースの規則の固定検査に書き換え。元のBOM明細ベースの文言が残らないことの検査を含む。未確認の列挙から `source_bom_item_id` が外れたことの検査）、`test_analysis_routing_step_material_view.py`・`test_analysis_bom_item_view.py`（新しい記述の固定検査）。`check_no_fixed_values`（2桁以上の数字・具体コード・許可外の大文字語の禁止）は変更していない。
- 仕様書: 本節、`AI運用規約・AI用DB辞書.md` 6.5-11・6.5-12、`AI分析基盤仕様書.md` のビュー一覧（2行）。

### 30.6 反映状況
コードのみ・DB変更なし（説明文は定義ファイルにあるため、バックエンド再起動で反映）。evaluator未検証。generator が実行した範囲（訂正後）: 対象8モジュールの試験（SimpleTestCase系、156件OK・skipped=2）、`pm-ui/scripts/test-analysis-*.mjs` 7本 fail 0、変異試験17件（メモリ上の差し替え。すべて検出）、開発DBの読み取りでの新しい規則の確認（§30.4）。分析での再確認（unknown が減るか）はBOSSが行う。コミット: 訂正分は未。
2026-10-12 追加訂正（§30.4-2）: 説明文2か所と試験（`test_description_has_bom_item_link_and_coproduct_rule`）、本仕様書、DB辞書6.5-12、基盤仕様書のビュー一覧を訂正。外部結合の1文を追加。コードのみ・DB変更なし。evaluator検証済み（2026-10-12。条件付き→本更新で対応）。再検証は未。コミット未。

## 30.7 本番DBの反映状況（2026-10-12。BOSSが本番のAdminerで確認・実行）
- 本番 `pm_db` に、AI用ビュー16個（`v_ai_*`）が、存在する（migrate ai 0050 まで適用済み）。
- 確認時点（付け替え前）：`v_ai_shipment`・`v_ai_purchase_receipt` の定義者は `pm_ai_view_owner@localhost`、残り14個は `root@%`（migrate を実行したユーザーのまま）だった。
- 本番のユーザー：`pm_ai_reader@172.18.%`（Dockerのネットワーク）、`pm_ai_view_owner@localhost`。
- 実行（BOSS）：`output/prod_ai_views_definer.sql`（`setup_ai_views.py`・登録・マイグレーションから自動生成。列権限の付与、単純なマスタビュー5つと結合ビュー9つの定義者付き再作成、`pm_ai_reader` へのビューの SELECT の付与、確認SQL）。
- **実行後の確認（2026-10-12）**：16個すべての定義者が `pm_ai_view_owner@localhost`・DEFINER。`pm_ai_view_owner` の権限は、公開列の列単位 SELECT だけ（表全体の SELECT なし。`v_ai_shipment` 用の `t_shipment_actual` 8列と、`v_ai_purchase_receipt` 用の `t_process_realtime_record` 9列を含む）。
- **既知の差異（今回は変更しない）**：本番の `pm_ai_reader@172.18.%` は、`pm_db.*` 全体の SELECT を持つ（開発と同じ）。ビューだけの権限ではない。理由：チャットの読み取り専用SQL（`SCREEN_SQL_TABLES`）が、ビューではなく元テーブル（`m_product`・`t_order` など）を、読み取り専用接続で直接読むため。`pm_db.*` の SELECT を取り消すと、チャットのSQLが使えなくなる。ビューだけにするには、チャットを、ビュー経由に切り替える必要がある（「将来はAIもDBを直接読まない」方針と同時に判断）。本番では分析の実行は無効（`pm_ai_reader` を使う経路はチャットのSQLだけ）。


## 31. ルーティング親品ID化（2026-10-12、BOSS承認済み／DB未反映）
- 親品の取得元を文字列から `m_routing_step.parent_product_id` に変更。`ai/0051` は既存0042/0043を変更せず、新しいFK経由で品番マスタの現在コードを返す。
- `v_ai_routing_step` は33列、`v_ai_routing_step_material` は20列を維持。列名／順序を変更せず、親品未指定はNULL。PK LEFT JOINで行数を維持し、旧remarkフォールバックなし。
- `setup_ai_views.OTHER_VIEW_COLUMNS` の工程列SELECTを `remark` → `parent_product_id` へ置換。専用SQL `scripts/routing_parent_ai_views_definer.sql.txt` はownerへの新列SELECT、2ビューのDEFINER再作成、未使用旧remark列SELECTの取り消しをまとめる。他ビューから旧列への参照がないことと本番アカウントは直前確認する。
- 通常移行でownerはmigrate実行者に戻るため、既存全ビュー用setupの実行だけでは2結合ビューのDEFINERが戻らない。全件親品移行 → ai/0051 → 専用SQLで2ビューの定義者を戻す。詳細は `ルーティング親品ID化実装計画.md`。

## 32. 設備マスタのビュー `v_ai_equipment` の作成前確認・実装記録（2026-10-15。BOSS承認済み。実装済み・evaluator未検証）

### 32.1 作成前確認

| 確認項目 | 内容 |
|---|---|
| 業務目的 | AIが、設備をコード・名前・所属ライン・所属工程で、分析・説明できるようにする |
| 元テーブル | `m_equipment`（設備マスタ）の1つだけ。結合なし（全17行。開発DBで確認） |
| 対象行 | 全行（WHEREなし）。`is_active=1`が有効 |
| 数値定義 | なし（マスタ）。件数は行数 |
| 公開フィールド（6列） | `id`、`equipment_code`、`equipment_name`、`is_active`、`line_id`、`process_id` |
| 非公開フィールド | `display_order`、`notes`、`created_at`、`updated_at` |
| 個人情報 | なし（設備コード・設備名・ID） |

#### 32.1.1 列型の対応（`SHOW COLUMNS FROM m_equipment`。開発DBで実測。ビュー作成後に再確認する）
| 列 | MySQL型 | `ANALYSIS_COLUMN_TYPES` |
|---|---|---|
| `id` | bigint | `BIGINT` |
| `equipment_code` | varchar(30) | `VARCHAR` |
| `equipment_name` | varchar(100) | `VARCHAR` |
| `is_active` | tinyint(1) | `BIGINT`（他の真偽値列と同じ表記規則。0/1） |
| `line_id` | bigint（NULL可） | `BIGINT` |
| `process_id` | bigint（NULL可） | `BIGINT` |

#### 32.1.2 NULL process_id の実データ確認
- 開発DBで `process_id IS NULL` は3行（全17行中）。該当は `YB-006`・`YB-009`・`YB-010`（いずれも `line_id=9`、`is_active=1`）。
- `m_line.id=9`（ブレーキライン）には `m_process` が2件（`process_code=4010`・`4040`）あり、この3設備は両工程で共用されるため `process_id` が単一に決まらずNULLと判断した（1工程に絞れない設備があることの説明として、`ANALYSIS_VIEWS['v_ai_equipment']['description']` に記載）。
- 説明文には、工程名・ラインの具体名（得意先名を含む語）は書かない。既存の固定試験（`test_analysis_column_guide.test_no_real_data_note_and_no_unconfirmed_meaning`）が、全ビューのdescriptionを連結して特定の得意先名の語（「クボタ」。`v_ai_line`のOTHER区分の1箇所だけ例外）を禁止しているため、process_codeの数字（`4010`・`4040`）だけで説明し、工程名の文字列は書かない。

### 32.2 実装内容

- `pm_backend/apps/ai/migrations/0054_ai_equipment_view.py` 新規。`CREATE OR REPLACE VIEW v_ai_equipment AS SELECT <6列> FROM m_equipment`（標準SQLのみ・別名なし・WHEREなし・結合なし）。ロールバックは `DROP VIEW IF EXISTS v_ai_equipment`。依存は `ai 0053_add_anthropic_provider` と `masters 0035_equipment_process`（`m_equipment` の6列は、`masters 0034_equipment`〜`0035_equipment_process` で揃っており、現時点の最新 `masters 0087` まで `m_equipment` への変更はない）。`makemigrations --dry-run --check` は「No changes detected」（ai・masters限定）。
- `sql_queries.py`：`BASE_SQL_SCHEMA` に `v_ai_equipment`（6列）を `v_ai_line` の直後に追加。
- `analysis_data_service.py`：`ANALYSIS_VIEWS` に `v_ai_equipment`（label=設備マスタ、`date_field=None`、`quantity_field=None`）を `v_ai_line` の直後に追加。
- `analysis_execution_service.py`：`ANALYSIS_COLUMN_TYPES` に `v_ai_equipment`（6列。§32.1.1）を `v_ai_line` の直後に追加。
- `setup_ai_views.py`：`SIMPLE_MASTER_VIEWS` に `v_ai_equipment`→`m_equipment` を1行追加（これ以外の変更なし）。単純なマスタビューは6つになった。
- 試験：`apps/ai/test_analysis_equipment_view.py` 新規（11件）。`test_setup_ai_views.py` は `LATEST_MIGRATION` に `v_ai_equipment`→`0054_ai_equipment_view.py` を追加、`--views` 絞り込みの試験の「対象外の語」に `m_equipment`・`v_ai_equipment` を追加（検査を強める方向。検査を弱めた箇所はない）。
- 既存7ビュー（出荷・入荷・品番・工程・ライン・仕入先・得意先）の定義（説明・列）のJSONのSHA-256（新規試験の固定値）：`db31acbfe065946a26dc439a40b4076ca41530869749bedf1f92e06600a410ed`（v_ai_equipment の追加前後で同一になることを確認）。

#### 32.2.1 承認済み計画からの逸脱（evaluatorへの確認依頼）
1. **`TABLE_NOTES`（`sql_queries.py`）への追加は見送った**：承認された実装計画の本文（項目2）には `BASE_SQL_SCHEMA` への追加だけが明記され、`TABLE_NOTES` への追加は含まれていなかった。一方、既存の全ての `v_ai_*` ビューは `BASE_SQL_SCHEMA` と `TABLE_NOTES` の両方にエントリを持つ（LLMへの自由SQL生成の説明に使われる）。計画にない変更を無断で行わないため、本実装では `TABLE_NOTES['v_ai_equipment']` を追加せず、新規試験 `test_analysis_equipment_view.py` も `TABLE_NOTES` を検証しない形にした。自由SQL生成機能では、このビューの説明が渡らない状態になる。追加要否はBOSSの確認が必要。→ **2026-10-15、BOSS承認により解消（§32.5参照）**。
2. **説明文の文言を承認済み計画の文言から変更した**：承認済み計画は「4010ブレーキティエラ・4040ブレーキクボタ」という工程名（得意先名を含む）を説明文に書く案だったが、§32.1.2のとおり既存の固定試験（得意先名「クボタ」の使用禁止。`v_ai_line`のOTHER区分の1箇所だけ例外）に抵触するため、`process_code=4010・4040`という工程コードの数字だけに書き換えた。業務上の意味（process_idがNULLになる理由）は変えていない。

### 32.3 検証結果（開発。読み取りのみ。テスト用DBは未整備のため、SimpleTestCase系のみ実行）
- `ai.test_analysis_equipment_view`（11件）単独でOK。
- `ai.test_analysis_equipment_view`・`test_setup_ai_views`・`test_analysis_routing_step_view`・`test_analysis_routing_step_material_view`・`test_analysis_bom_item_view`・`test_analysis_leader_unit_view`・`test_analysis_supervisor_team_view`・`test_analysis_unit_line_view`・`test_analysis_user_view`・`test_analysis_department_view`・`test_analysis_column_guide`・`test_analysis_calendar_day_view`・`test_analysis_customer_view`・`test_analysis_supplier_view`・`test_analysis_line_view`・`test_analysis_process_view`・`test_analysis_product_view`・`test_analysis_dateless_view`・`test_analysis_execution` の1コマンド実行で297件中295件OK（skipped=2）。残り2件の失敗（`test_analysis_bom_item_view.test_migration_dependency_exists_and_covers_source_columns`・`test_analysis_user_view.test_migration_dependency_exists`）は、masters・accountsアプリの最新マイグレーションのファイル名が、試験の固定値（`0086`・`0072`）より進んでいる（実際は`0087`・`0073`）ことによるもので、本実装（設備ビュー）とは無関係の既存の食い違い（本件着手前から存在）。
- `python manage.py makemigrations ai masters --dry-run --check`：「No changes detected in apps 'masters', 'ai'」。
- `CREATE VIEW` の実行（`migrate`・`setup_ai_views --apply`）は、禁止事項のため実行していない。開発DBへのビュー反映・`pm_ai_reader`での読み取り確認・`SHOW COLUMNS FROM v_ai_equipment`での列型の再確認は、未実施（evaluatorまたはBOSSの確認が必要）。

### 32.4 反映状況
- コードのみ・マイグレーションファイルの新規作成のみ（`migrate`は未実行）。開発DB・本番DBともに `v_ai_equipment` ビューは未作成。
- 評価：evaluator未検証（条件付き合格。指摘事項「`TABLE_NOTES`欠落」はBOSS承認を得て§32.5で解消）。
- コミット：未（BOSSの指示後に実施）。
- generator実行試験: SQLiteメモリ上で新旧公開列名/順序、行数、コード改名の伝播を確認。新親品／AI既存定義／受注中間工程試験48件OK。MySQLの実DDL／本番権限、実DB移行は未確認・未実行。独立evaluator判定待ち。

### 32.5 追加修正: `TABLE_NOTES` への追加（2026-10-15。BOSS承認済み。§32.2.1-1の解消）

前回のevaluatorが「`TABLE_NOTES`欠落」を条件付き合格の指摘事項として挙げ、BOSSが追加を承認したため、以下だけを実装した（他ファイルの変更なし）。

- `pm_backend/apps/ai/services/sql_queries.py`：`TABLE_NOTES` 辞書に `v_ai_equipment` を `v_ai_line` の直後に追加（6行）。文言は §32.1.2 の得意先名禁止規則を踏まえ、`process_code 4010・4040` という番号表記のみを使用（工程名・得意先名の固有文字列は書かない）。`ANALYSIS_VIEWS['v_ai_equipment']['description']`・`BASE_SQL_SCHEMA`・`ANALYSIS_COLUMN_TYPES`・`SIMPLE_MASTER_VIEWS`・マイグレーション本体は変更していない。
- `pm_backend/apps/ai/test_analysis_equipment_view.py`：冒頭の注記を更新（TABLE_NOTES追加済みである旨）。他の単純マスタビュー試験（`test_analysis_line_view.py`等）と同様、`TABLE_NOTES[EQUIPMENT]` が存在し空でないこと・必要な文言を含むこと・得意先名「クボタ」を含まないことを検証する試験 `test_table_notes_entry_exists_and_is_not_empty` を1件追加。加えて、`schema_text('ai_home')` の出力に `v_ai_equipment` の節と `TABLE_NOTES` の本文が実際に含まれることを検証する試験 `test_table_notes_entry_is_included_in_ai_home_schema_text` を1件追加（`ai_home`画面の自由SQL生成プロンプトに渡ることの確認）。
- 検証結果：`python manage.py test ai.test_analysis_column_guide ai.test_analysis_equipment_view ai.test_setup_ai_views`（開発DB、SimpleTestCaseのみ）→ 54件OK（既存の得意先名禁止チェックを含む固定試験が全て通過）。
- `schema_text()`／`AI_HOME_EXCLUDED_TABLES`の確認：`AI_HOME_EXCLUDED_TABLES`に`v_ai_equipment`は含まれず、`SCREEN_SQL_TABLES['ai_home']`は`BASE_SQL_SCHEMA`の全キー（`v_ai_equipment`を含む）から除外集合を引いた集合のため、`v_ai_equipment`は対象に入る。`schema_text('ai_home')`は`allowed_tables_for_screen`で取得した対象テーブルごとに`TABLE_NOTES.get(table)`があれば本文を付加するため、`v_ai_equipment`のTABLE_NOTESは実際に`ai_home`画面の自由SQL生成プロンプトに含まれる（新規試験で機械的に確認済み）。
- 反映状況：コードのみ・DB変更なし（`migrate`・`setup_ai_views --apply`は未実行、禁止事項のため実施していない）。コミット・push・本番反映は未（BOSSの指示後）。
- 省略した点：`ANALYSIS_VIEWS`・`BASE_SQL_SCHEMA`・`ANALYSIS_COLUMN_TYPES`・`SIMPLE_MASTER_VIEWS`・マイグレーション本体・コミット・migrateは、今回の指示どおり変更していない。

## 33. 一般工程 生産実績のビュー `v_ai_process_production_actual` の作成前確認・実装記録（2026-10-17。BOSS承認済み。実装済み・evaluator未検証）

### 33.0 追記（2026-10-17。BOSSが公開列構成を変更。本節は2回目の実装）

evaluatorの条件付き合格後、BOSSが公開列構成を次のとおり変更した（generatorが実装）。

- **`operator_name`を公開列に追加**（従来は非公開）。
- **`event_data`を公開列から除外**（非公開に変更）。理由：`analysis_execution_service.py`の`_cell()`関数がJSON型のCSV変換に対応しておらず、このビューで`event_data`を分析実行すると100%失敗することが、evaluatorの実機検証（開発DBへの実際のビュー作成を含む）で確認されたため（§33.3-1で元々懸念として記録していた点が、実機検証で実際に再現した）。

以降の本節の内容は、この変更後の最終状態（公開14列）に更新している。変更前の記録（公開列に`event_data`、非公開に`operator_name`としていた版）は、Gitの差分履歴で確認できる。

### 33.1 作成前確認

| 確認項目 | 内容 |
|---|---|
| 業務目的 | AIが、一般工程の生産実績(品番・数量・記録時刻・設備状態など)を、業務日(8時区切り)で分析・説明できるようにする |
| 元テーブル | `t_process_realtime_record`（工程実時間記録）。`record_type='PRODUCTION'`の行だけ |
| 対象行 | `WHERE record_type = 'PRODUCTION'` |
| 数値定義 | `qty`=生産数量。`business_day`(計算列。`DATE(timestamp - INTERVAL 8 HOUR)`、8時区切りの業務日) |
| 公開フィールド（14列。元テーブル16列中。BOSS判断で確定。2026-10-17にBOSSが変更） | `id`、`business_day`(新規の計算列)、`operator_login_id`、`operator_name`、`process_id`、`product_code`、`product_id`、`product_name`、`qty`、`record_type`、`timestamp`、`equipment_state`、`interruption_reason_code`、`remarks` |
| 非公開フィールド | `batch_no`、`event_data` |
| 個人情報 | `operator_login_id`はログインID(`auth_user.username`)で、既存の`v_ai_user`と同じ扱い(個人名そのものではない)。`operator_name`は作業者名(個人名)で、2026-10-17にBOSS判断で公開に変更した。元テーブル`t_process_realtime_record`の`operator_name`は、チャットSQL（`sql_queries.py`の`PERSONAL_SQL_COLUMNS`・`SENSITIVE_IDENTIFIER`）では個人情報の権限がないと参照できない扱いのままで、これは変更していない（本ビューの分析実行パス(`ANALYSIS_VIEWS`)は、チャットSQLのパス(`SCREEN_SQL_TABLES`・`_validate_sql`)とは別の仕組みで、既存の`v_ai_user`(姓・名)・`v_ai_customer`(得意先名)と同様に、分析実行では氏名等を個人情報の権限で別途絞っていない前例に合わせた。矛盾ではなく既存の前例どおり）。`remarks`は自由記述で、業務上の記載内容は未確認(非公開の`batch_no`とは異なり、BOSS判断で公開) |

#### 33.1.1 `business_day`の計算ロジックの確認（開発DB実データ、全件）

- 8時区切りの業務日判定の正規ロジックは、Python側の`production/serializers_process_realtime.py`の`resolve_workday_date_for_process(process, dt)`（`dt.time() < 8:00`なら前日、以降はラインの勤務カレンダのセグメントで夜勤跨ぎを判定し、通常は当日）。
- ビューの計算列は、このロジックを単純化した`DATE(timestamp - INTERVAL 8 HOUR)`（8時間引いた日付）。
- generatorが、Django ORM経由で開発DBの`t_process_realtime_record`の`record_type='PRODUCTION'`行を全件読み、`DATE(timestamp - INTERVAL 8 HOUR)`のPython再現値と`resolve_workday_date_for_process()`の返り値を1件ごとに比較した。結果：**全15,731件で一致（不一致0件）**。
- この一致は、本番運用で稼働開始時刻が8時以外のラインが存在しないことをBOSSが確認済みであることに基づく（勤務カレンダのセグメント判定が、8時起点の単純な日付境界と食い違う状況が、現在の運用データには存在しない）。将来、8時以外に稼働を開始するラインができた場合は、この一致が崩れる可能性があるため、再確認が必要。

### 33.2 実装内容

- 新規 `pm_backend/apps/ai/migrations/0055_ai_process_production_actual_view.py`。`CREATE OR REPLACE VIEW v_ai_process_production_actual AS SELECT <14列> FROM t_process_realtime_record WHERE record_type = 'PRODUCTION'`（標準SQLのみ・バッククォート/DEFINER/SQL SECURITY/DB修飾なし）。ロールバックは`DROP VIEW IF EXISTS v_ai_process_production_actual`。依存は`ai 0054_ai_equipment_view`と`production 0124_processrealtimerecord_interruption_reason_code`（`interruption_reason_code`列の追加マイグレーション。`operator_login_id`列は、その前の`production 0119_process_realtime_operator_login_id`で追加済みで、0124への依存に含まれる）。
- `pm_backend/apps/ai/services/sql_queries.py`：`BASE_SQL_SCHEMA`に`v_ai_process_production_actual`（14列。マイグレーションのSELECT順と同じ）を`v_ai_shipment`の直後に追加。`TABLE_NOTES`にも同じ位置に追加（§33.1の内容、`interruption_reason_code`が常に空文字になる旨、`operator_login_id`が`auth_user.username`と結べる旨、`process_id`・`product_id`がそれぞれ`v_ai_process`・`v_ai_product`の`id`と結べる旨、`operator_name`が作業者名である旨を明記。2026-10-17の変更で、`event_data`がJSON列である旨の記述は削除した）。
- `pm_backend/apps/ai/services/analysis_data_service.py`：`ANALYSIS_VIEWS`に`v_ai_process_production_actual`（label=一般工程生産実績、`date_field='business_day'`、`quantity_field='qty'`、説明文）を`v_ai_shipment`の直後に追加。
- `pm_backend/apps/ai/services/analysis_execution_service.py`：`ANALYSIS_COLUMN_TYPES`に14列の型を追加（§33.1.2の型対応）を`v_ai_shipment`の直後に追加。
- `pm_backend/apps/ai/management/commands/setup_ai_views.py`：`EXISTING_JOIN_VIEWS`に`v_ai_process_production_actual`を追加（`v_ai_purchase_receipt`と同じ「結合なし・WHERE句あり」の扱い。再作成しない。`--check`で定義者等を表示するだけ）。`SIMPLE_MASTER_VIEWS`・`OTHER_VIEW_COLUMNS`は変更していない（§33.3の判断参照）。
- 試験：`apps/ai/test_analysis_process_production_actual_view.py`新規（2026-10-17の変更後は20件。既存の`v_ai_purchase_receipt`・`v_ai_shipment`と同様、SimpleTestCaseのみ（開発DBへは接続しない）。公開列の変更に合わせて`PUBLISHED`・`HIDDEN`・`ANALYSIS_COLUMN_TYPES`の期待値を更新し、`operator_name`が公開列であること・`event_data`が非公開であることを検証する新規テストを1件追加）。
- 仕様書：本節、`AI運用規約・AI用DB辞書.md`に新規節を追加。

#### 33.1.2 列型の対応（`SHOW COLUMNS FROM t_process_realtime_record`。開発DBで実測。2026-10-17に`operator_name`を追加・`event_data`を削除）

| 列 | MySQL型 | `ANALYSIS_COLUMN_TYPES` |
|---|---|---|
| `id` | bigint | `BIGINT` |
| `business_day` | (計算列。実列はない) | `DATE` |
| `operator_login_id` | varchar(150)、NULL可 | `VARCHAR` |
| `operator_name` | varchar(50)、NULL可 | `VARCHAR` |
| `process_id` | bigint | `BIGINT` |
| `product_code` | varchar(50)、NULL可 | `VARCHAR` |
| `product_id` | bigint、NULL可 | `BIGINT` |
| `product_name` | varchar(100)、NULL可 | `VARCHAR` |
| `qty` | decimal(10,3) | `DECIMAL(18,3)` |
| `record_type` | varchar(20) | `VARCHAR` |
| `timestamp` | datetime(6) | `TIMESTAMP` |
| `equipment_state` | varchar(20)、NULL可 | `VARCHAR` |
| `interruption_reason_code` | varchar(4) | `VARCHAR` |
| `remarks` | longtext、NULL可 | `VARCHAR` |

参考（非公開に変更。2026-10-17以降は`ANALYSIS_COLUMN_TYPES`に含めない）：`event_data`は json、NULL可。公開していた当時は`ANALYSIS_COLUMN_TYPES`で`JSON`としていたが、§33.3-1の課題（`_cell()`がJSON型の変換に未対応で分析実行が失敗する）がevaluatorの実機検証で実際に再現したため、BOSS判断で非公開に変更した。

### 33.3 承認済み計画からの逸脱・不確実な点（evaluatorへの確認依頼）

1. **`event_data`の型`JSON`は、このAI分析パイプラインで前例がない**。`ANALYSIS_COLUMN_TYPES`に`JSON`型を持つ列は、本ビューが最初（既存の16ビューにJSON列はない）。さらに、実行時に値をDuckDB投入用CSVへ変換する`analysis_execution_service._cell()`には、`BIGINT`・`DATE`・`TIMESTAMP`・`DECIMAL(p,s)`・`VARCHAR`の分岐しかなく、`JSON`型の分岐がない。そのため、現状のコードのまま分析実行で`event_data`列を選択すると、`_cell()`が`ExecutionStopped('unsupported_value', ...)`で失敗する（計画書の指示どおり`ANALYSIS_COLUMN_TYPES`へ`JSON`を追加したのみで、`_cell()`の拡張は計画の範囲外のため実装していない）。**BOSSへの確認が必要**：`_cell()`へ`JSON`分岐を追加する別サイクルが必要か、それまで`event_data`を実運用で選択させない運用上の注意が必要か。
   - **追記（2026-10-17。対応済み）**：evaluatorが開発DBへ実際にビューを作成して実機検証した結果、`event_data`列を選択した分析実行は**100%失敗**することが確認された。BOSSが、この課題への対応として`event_data`を公開列から除外（非公開に変更）することを決定した。代わりに`operator_name`を公開列に追加した（§33.0）。これにより、本課題はコード上の対応（`_cell()`拡張）ではなく、公開範囲の変更で解消した。将来、`event_data`の分析ニーズが生じた場合は、`_cell()`へJSON分岐を追加する別サイクルを改めて計画すること。
2. **手順SQL（§33.4）の不足列は、計画の例示（`equipment_state`・`event_data`・`remarks`・`interruption_reason_code`等）と一部異なる**。開発DBで`information_schema.COLUMN_PRIVILEGES`を実確認した結果、`pm_ai_view_owner`は`t_process_realtime_record`の9列（`id`・`event_data`・`process_id`・`product_code`・`product_id`・`product_name`・`qty`・`record_type`・`timestamp`。既存`v_ai_purchase_receipt`用）のSELECTを既に持っており、`event_data`は不足していない。実際に不足しているのは`equipment_state`・`interruption_reason_code`・`operator_login_id`・`remarks`の4列（計画の例示に`operator_login_id`はなかった）。DB実データの確認結果を優先し、手順SQL（§33.4）はこの4列のGRANTにした。
   - **追記（2026-10-17）**：公開列変更（§33.0）に伴い、`operator_name`のGRANTが新たに必要になった。開発DBで再確認した結果、`pm_ai_view_owner`は`operator_name`のSELECTを持っていない（他の列への付与経緯も含め不足は変わらず）。`event_data`は、本ビューでは不要になったが、既存の付与（`v_ai_purchase_receipt`用、本ビューとは無関係に以前から付与されていたもの）はそのまま残っており、本変更でREVOKEは行っていない（計画の範囲外）。手順SQL（§33.4）の不足列を、`equipment_state`・`interruption_reason_code`・`operator_login_id`・`operator_name`・`remarks`の5列に更新した。
3. **`setup_ai_views.py`の`SIMPLE_MASTER_VIEWS`は使わない**（計画どおり。WHERE句付きのため）。これに伴い、`test_setup_ai_views.py`の`LATEST_MIGRATION`辞書は更新していない。`LATEST_MIGRATION`は`SIMPLE_MASTER_VIEWS`のビュー専用の対応表（`test_migration_columns_match_command`が、エイリアス・計算式のない素の列名リストを前提に、`FROM`先が`cmd.SIMPLE_MASTER_VIEWS[view]`と一致することを検査する）で、本ビューはWHERE句・計算列（`DATE(timestamp - INTERVAL 8 HOUR) AS business_day`）を持つため、この対応表に追加すると検査が成立しない（`cmd.SIMPLE_MASTER_VIEWS[view]`で`KeyError`になるか、列名の不一致で失敗する）。本ビューを`EXISTING_JOIN_VIEWS`へ追加したことで、既存の汎用試験`test_does_not_recreate_join_views`（`cmd.EXISTING_JOIN_VIEWS`を走査する）が自動的に本ビューも対象にする。**BOSSへの確認が必要**：計画書の「7. `test_setup_ai_views.py`の`LATEST_MIGRATION`更新」は、本ビューの性質（WHERE句付き）と矛盾するため、実装せずこの逸脱として報告する。
4. **`setup_ai_views.py`の`OTHER_VIEW_COLUMNS`に`t_process_realtime_record`を追加していない**。`v_ai_bom_item`・`v_ai_routing_step`等（§26〜30）の前例では、結合ビューの元テーブル（`FROM`の主テーブルを含む）をすべて`OTHER_VIEW_COLUMNS`に記録しているが、`v_ai_purchase_receipt`・`v_ai_shipment`（§2。本ビューと同じく`t_process_realtime_record`・`t_shipment_actual`が主テーブル）は、`OTHER_VIEW_COLUMNS`に記録されていない（コマンドのコメント「`t_shipment_actual`の列は対象外」のとおり）。`OTHER_VIEW_COLUMNS`は、`SIMPLE_MASTER_VIEWS`のソーステーブル（`m_product`等）を再作成する際に、結合ビューが必要とする列を誤ってREVOKEしないための一覧だが、`t_process_realtime_record`は`SIMPLE_MASTER_VIEWS`のソーステーブルではないため、追加しても`build_plan`・`run_check`の動作には影響しない（ドキュメント目的のみ）。本実装は、直接の前例である`v_ai_purchase_receipt`と同じ扱い（追加しない）を選んだ。**BOSSの判断が必要**：後発の結合ビュー群の慣習（主テーブルも記録する）に合わせるなら追加する。

### 33.4 手順SQL（`pm_ai_view_owner`への列権限と定義者の付け替え。MySQL固有のため手動。実行はBOSS。`<db>`は接続先のDB名。管理者で実行。`migrate ai 0055`の後）

開発DB再確認済み（`information_schema.COLUMN_PRIVILEGES`、2026-10-17。§33.0の公開列変更後）：`pm_ai_view_owner`は`t_process_realtime_record`の`id`・`event_data`・`process_id`・`product_code`・`product_id`・`product_name`・`qty`・`record_type`・`timestamp`の9列のSELECTを既に持つ（既存`v_ai_purchase_receipt`用）。不足は`equipment_state`・`interruption_reason_code`・`operator_login_id`・`operator_name`・`remarks`の5列（`operator_name`は今回の公開列変更で新たに不足した列。`event_data`は本ビューでは不要になったが、既存の付与はそのまま残す。REVOKEは計画の範囲外のため行わない）。

```sql
GRANT SELECT (`equipment_state`, `interruption_reason_code`, `operator_login_id`, `operator_name`, `remarks`) ON `<db>`.`t_process_realtime_record` TO 'pm_ai_view_owner'@'localhost';
CREATE OR REPLACE DEFINER = 'pm_ai_view_owner'@'localhost' SQL SECURITY DEFINER VIEW `<db>`.`v_ai_process_production_actual` AS
SELECT
    `id`,
    DATE(`timestamp` - INTERVAL 8 HOUR) AS `business_day`,
    `operator_login_id`,
    `operator_name`,
    `process_id`,
    `product_code`,
    `product_id`,
    `product_name`,
    `qty`,
    `record_type`,
    `timestamp`,
    `equipment_state`,
    `interruption_reason_code`,
    `remarks`
FROM `<db>`.`t_process_realtime_record`
WHERE `record_type` = 'PRODUCTION';
GRANT SELECT ON `<db>`.`v_ai_process_production_actual` TO 'pm_ai_reader'@'<readerのホスト部>';  -- 開発のreaderがDB全体のSELECTを持つ場合は不要
```

手順SQLのビュー定義は、マイグレーション0055のSELECT（標準SQL）と、列・式・順序が同じであること（バッククォート・`<db>`の修飾は手動SQLだけに付ける）。

**未実行**（本節の作成時点では、GRANT・CREATE・DEFINER付け替えのいずれも実行していない。計画の禁止事項により実行は行わない。実行はBOSS）。

### 33.5 検証結果（generatorが実行。開発。読み取りのみ）

#### 33.5.1 初回実装（公開列にevent_data・非公開にoperator_name）時点

- `python manage.py test ai.test_analysis_process_production_actual_view --keepdb`：16件OK（追加直後の単独実行）。
- `python manage.py test ai.test_analysis_process_production_actual_view ai.test_setup_ai_views ai.test_analysis_execution ai.test_analysis_column_guide ai.test_analysis_equipment_view ai.test_analysis_calendar_day_view ai.test_analysis_bom_item_view ai.test_analysis_routing_step_view ai.test_analysis_routing_step_material_view ai.test_analysis_user_view ai.test_analysis_department_view ai.test_analysis_supplier_view ai.test_analysis_customer_view ai.test_analysis_line_view ai.test_analysis_process_view ai.test_analysis_product_view ai.test_analysis_dateless_view ai.test_analysis_supervisor_team_view ai.test_analysis_leader_unit_view ai.test_analysis_unit_line_view --keepdb`：315件中313件OK（skipped=2）。残り2件の失敗（`test_analysis_bom_item_view.test_migration_dependency_exists_and_covers_source_columns`・`test_analysis_user_view.test_migration_dependency_exists`）は、masters・accountsアプリの最新マイグレーションのファイル名が試験の固定値よりさらに進んでいること（`0092`・`0075`、§32.3時点では`0087`・`0073`）が原因で、本実装（本ビュー）とは無関係の既存の食い違い（本件着手前から存在、進行中）。
- `python manage.py makemigrations --dry-run --check`：「No changes detected」。
- `business_day`の全件突き合わせ（§33.1.1。Django ORM、開発DB）：**全15,731件中、一致15,731件・不一致0件**。
- `CREATE VIEW`の実行（`migrate`・`setup_ai_views --apply`・§33.4の手順SQL）は、禁止事項のため実行していない。開発DBへのビュー反映・`pm_ai_reader`での読み取り確認・`SHOW COLUMNS FROM v_ai_process_production_actual`での列型の再確認・`event_data`列を含む分析実行（§33.3-1の`_cell()`未対応の影響範囲の実機確認）は、未実施（evaluatorまたはBOSSの確認が必要）。

#### 33.5.2 2回目の修正（2026-10-17。公開列をoperator_name追加・event_data除外に変更）時点

- `python manage.py makemigrations --dry-run --check`：「No changes detected」（モデル変更を伴わないビューSQLの変更のため、新規マイグレーションは発生しない）。
- `python manage.py test ai.test_analysis_process_production_actual_view --keepdb`：**17件OK**（単独実行。新規追加した`test_operator_name_is_published_and_event_data_is_hidden`を含む）。
- 上記と同じ20ビュー分の関連試験一括実行（`ai.test_analysis_process_production_actual_view ai.test_setup_ai_views ai.test_analysis_execution ...`、`--keepdb`）：**316件中314件OK（skipped=2）**。失敗2件は初回実装時と同じ既存の食い違い（`test_analysis_bom_item_view.test_migration_dependency_exists_and_covers_source_columns`・`test_analysis_user_view.test_migration_dependency_exists`。masters・accountsの最新マイグレーションファイル名のズレ）で、本変更とは無関係。
- `operator_name`列の型（開発DB実データ確認。`SHOW COLUMNS FROM t_process_realtime_record WHERE Field='operator_name'`）：**varchar(50)、NULL可**。`ANALYSIS_COLUMN_TYPES`は既存の`VARCHAR`表記に合わせた。
- `pm_ai_view_owner`の列権限（開発DB実データ確認。`information_schema.COLUMN_PRIVILEGES`）：`operator_name`へのSELECTは**まだ付与されていない**（§33.4の手順SQLを更新。未実行・BOSSが実行）。`event_data`へのSELECTは既存のまま残っている（本ビュー用ではなく元から付与されていたもの。REVOKEは行っていない）。
- `CREATE VIEW`の実行（`migrate`・`setup_ai_views --apply`・§33.4の手順SQL）は、本変更でも禁止事項のため実行していない。開発DBへのビュー反映・`pm_ai_reader`での読み取り確認・`operator_name`を含む分析実行の実機確認は、未実施（evaluatorまたはBOSSの確認が必要）。

### 33.6 反映状況

- コードのみ・マイグレーションファイル（既存の`0055`を書き換え。新規マイグレーション番号は追加していない）。開発DB・本番DBともに`v_ai_process_production_actual`ビューは未作成（`migrate`未実行）。手順SQL（§33.4）も未実行。
- 評価：初回実装はevaluator条件付き合格（実機検証で`event_data`の分析実行失敗を確認）。2026-10-17の本修正（公開列変更）は、まだevaluator未検証。
- コミット：未（BOSSの指示後に実施）。
- 未確認・未実施：`pm_ai_reader`の列権限・読み取り確認、`operator_name`を含む分析実行の実機確認、本番反映、evaluatorによる独立検証（2回目の修正分）。

## 34. レーザー 生産実績のビュー `v_ai_laser_production_actual` の作成前確認・実装記録（2026-10-17。BOSS承認済み。コード実装・開発DBへの`ai/0056`適用済み・evaluator第1回条件付き）

### 34.1 作成前確認

| 確認項目 | 内容 |
|---|---|
| 業務目的 | AIが、レーザーの生産実績(構成部品・使用材料・数量・作業日・設備・作業者アクションなど)を分析・説明できるようにする |
| 元テーブル | `t_laser_actual`（レーザー実績ヘッダ）に`t_laser_actual_detail`（構成部品明細）を結合。`actual_id`で結合 |
| 対象行 | `WHERE a.operator_action IN ('END', 'PAUSE') AND d.detail_type = 'COMPONENT'`（終了・中断の確定済み行、かつ構成部品の明細行だけ） |
| 数値定義 | `total_qty`=構成部品換算数量（生産数に相当）。`work_date`=作業日（実列、計算列ではない） |
| 公開フィールド（31列。BOSS判断で確定） | `id`、`actual_id`、`operator_user_id`（`created_by_id`の別名）、`equipment_id`、`equipment_code`、`equipment_name`、`line_id`、`process_id`、`pattern_id`、`pattern_no`、`material_id`、`material_code`、`material_name`、`product_id`、`product_code`、`product_name`、`work_date`、`shot_count`、`process_time_per_shot`、`total_process_time`、`operator_action`、`operator_action_reason`、`units_per_shot`、`total_qty`、`scrap_qty`、`scrap_reason`、`end_operator_user_id`（`updated_by_id`の別名）、`created_at_h`、`updated_at_h`（ヘッダの作成・更新日時）、`created_at`、`updated_at`（無印。明細の作成・更新日時） |
| 非公開フィールド | `detail_type`（常に`COMPONENT`固定。WHEREの絞り込みにだけ使い、出力列には含めない）、`display_order`（画面の並び順）、ヘッダの`remarks`（開発DB確認済み：全件空。`t_laser_actual`4,997件中4,997件が空文字） |
| 個人情報 | `operator_user_id`・`end_operator_user_id`は`auth_user.id`へのFK（氏名そのものではない）。既存の`v_ai_process_production_actual`の`operator_login_id`と同様、本ビューはIDだけを公開し、氏名は公開しない |

#### 34.1.1 `line_id`・`process_id`がNULLになる期間の確認（開発DB実データ）

- `t_laser_actual`の`line_id`・`process_id`は、`production/migrations/0118_laser_actual_line_process.py`（2026-10-13作成）でライン・工程の保存機能を追加した列。
- generatorが開発DBで実データを確認：`work_date`の範囲は2026-03-16〜2026-10-15（実績全4,997件）で、`line_id IS NULL`の行は4,986件（ほぼ全件）。日別に絞って確認すると、2026-10-12は40件中40件がNULL、2026-10-13は45件中45件がNULL、**2026-10-14は10件中0件がNULL、2026-10-15は1件中0件がNULL**。2026-10-14を境に、NULLがゼロになることを確認した（BOSS確認済みの事実と一致）。
- そのため、本ビューの`line_id`・`process_id`が2026-10-14より前の行でNULLなのは、欠損ではなく、保存機能がなかった期間の仕様であることをTABLE_NOTESに明記する。

### 34.2 実装内容

- 新規 `pm_backend/apps/ai/migrations/0056_ai_laser_production_actual_view.py`。`CREATE OR REPLACE VIEW v_ai_laser_production_actual AS SELECT <31列> FROM t_laser_actual_detail d JOIN t_laser_actual a ON a.id = d.actual_id WHERE a.operator_action IN ('END', 'PAUSE') AND d.detail_type = 'COMPONENT'`（標準SQLのみ・バッククォート/DEFINER/SQL SECURITY/DB修飾なし。JOIN自体は許可）。ロールバックは`DROP VIEW IF EXISTS v_ai_laser_production_actual`。依存は`ai 0055_ai_process_production_actual_view`と`production 0118_laser_actual_line_process`（`line_id`・`process_id`列の追加マイグレーション）。
- `pm_backend/apps/ai/services/sql_queries.py`：`BASE_SQL_SCHEMA`に`v_ai_laser_production_actual`（31列。マイグレーションのSELECT順と同じ）を`v_ai_process_production_actual`の直後に追加。`TABLE_NOTES`にも同じ位置に追加（§34.1の内容、`line_id`・`process_id`が2026-10-14より前はNULLになる旨、`operator_user_id`・`end_operator_user_id`がそれぞれ`created_by_id`・`updated_by_id`の別名である旨、`material_*`は使用材料・`product_*`は構成部品である旨、`created_at_h`/`updated_at_h`がヘッダ・`created_at`/`updated_at`(無印)が明細自体の日時である旨を明記）。
- `pm_backend/apps/ai/services/analysis_data_service.py`：`ANALYSIS_VIEWS`に`v_ai_laser_production_actual`（label=レーザー生産実績、`date_field='work_date'`、`quantity_field='total_qty'`、説明文）を`v_ai_process_production_actual`の直後に追加。
- `pm_backend/apps/ai/services/analysis_execution_service.py`：`ANALYSIS_COLUMN_TYPES`に31列の型を追加（§34.1.2の型対応）を`v_ai_process_production_actual`の直後に追加。
- `pm_backend/apps/ai/management/commands/setup_ai_views.py`：`EXISTING_JOIN_VIEWS`に`v_ai_laser_production_actual`を追加（既存の`v_ai_process_production_actual`等と同じ「結合・WHERE句あり」の扱い。再作成しない。`--check`で定義者等を表示するだけ）。近くのコメントの対象マイグレーション番号の一覧に`0056`を追記。`SIMPLE_MASTER_VIEWS`・`OTHER_VIEW_COLUMNS`は変更していない（`t_laser_actual`・`t_laser_actual_detail`は他の公開ビューと列を共有しないため。§33の`v_ai_process_production_actual`と同じ扱い）。
- 試験：`apps/ai/test_analysis_laser_production_actual_view.py`新規（15件。既存の`v_ai_process_production_actual`と同様にSimpleTestCaseで列・型・公開列・非公開列・マイグレーションSQL・`setup_ai_views`登録を検証するテストに加え、開発DBの実テーブルへ直接読み取りだけを行う件数照合テストを追加）。`ai/0056`適用後、件数照合を含む15件すべてが成功した。
- 仕様書：本節、`AI運用規約・AI用DB辞書.md`に新規節（§6.5-18）を追加。

#### 34.1.2 列型の対応（`SHOW COLUMNS FROM t_laser_actual`・`SHOW COLUMNS FROM t_laser_actual_detail`。開発DBで実測）

| 列 | 元テーブル・MySQL型 | `ANALYSIS_COLUMN_TYPES` |
|---|---|---|
| `id` | `t_laser_actual_detail.id`、bigint | `BIGINT` |
| `actual_id` | `t_laser_actual_detail.actual_id`、bigint | `BIGINT` |
| `operator_user_id` | `t_laser_actual.created_by_id`、int、NULL可 | `BIGINT` |
| `equipment_id` | `t_laser_actual.equipment_id`、bigint | `BIGINT` |
| `equipment_code` | `t_laser_actual.equipment_code`、varchar(50) | `VARCHAR` |
| `equipment_name` | `t_laser_actual.equipment_name`、varchar(100) | `VARCHAR` |
| `line_id` | `t_laser_actual.line_id`、bigint、NULL可 | `BIGINT` |
| `process_id` | `t_laser_actual.process_id`、bigint、NULL可 | `BIGINT` |
| `pattern_id` | `t_laser_actual.pattern_id`、bigint | `BIGINT` |
| `pattern_no` | `t_laser_actual.pattern_no`、varchar(50) | `VARCHAR` |
| `material_id` | `t_laser_actual.material_id`、bigint、NULL可 | `BIGINT` |
| `material_code` | `t_laser_actual.material_code`、varchar(50) | `VARCHAR` |
| `material_name` | `t_laser_actual.material_name`、varchar(100) | `VARCHAR` |
| `product_id` | `t_laser_actual_detail.product_id`、bigint、NULL可 | `BIGINT` |
| `product_code` | `t_laser_actual_detail.product_code`、varchar(50) | `VARCHAR` |
| `product_name` | `t_laser_actual_detail.product_name`、varchar(100) | `VARCHAR` |
| `work_date` | `t_laser_actual.work_date`、date | `DATE` |
| `shot_count` | `t_laser_actual.shot_count`、int unsigned | `BIGINT` |
| `process_time_per_shot` | `t_laser_actual.process_time_per_shot`、decimal(10,1) | `DECIMAL(18,1)` |
| `total_process_time` | `t_laser_actual.total_process_time`、decimal(12,1) | `DECIMAL(18,1)` |
| `operator_action` | `t_laser_actual.operator_action`、varchar(20) | `VARCHAR` |
| `operator_action_reason` | `t_laser_actual.operator_action_reason`、varchar(200) | `VARCHAR` |
| `units_per_shot` | `t_laser_actual_detail.units_per_shot`、decimal(14,3) | `DECIMAL(18,3)` |
| `total_qty` | `t_laser_actual_detail.total_qty`、decimal(14,3) | `DECIMAL(18,3)` |
| `scrap_qty` | `t_laser_actual_detail.scrap_qty`、decimal(14,3) | `DECIMAL(18,3)` |
| `scrap_reason` | `t_laser_actual_detail.scrap_reason`、varchar(200) | `VARCHAR` |
| `end_operator_user_id` | `t_laser_actual.updated_by_id`、int、NULL可 | `BIGINT` |
| `created_at_h` | `t_laser_actual.created_at`、datetime(6) | `TIMESTAMP` |
| `updated_at_h` | `t_laser_actual.updated_at`、datetime(6) | `TIMESTAMP` |
| `created_at` | `t_laser_actual_detail.created_at`、datetime(6) | `TIMESTAMP` |
| `updated_at` | `t_laser_actual_detail.updated_at`、datetime(6) | `TIMESTAMP` |

参考（非公開。`ANALYSIS_COLUMN_TYPES`に含めない）：`t_laser_actual_detail.detail_type`はvarchar(20)でWHEREの絞り込みにだけ使う。`t_laser_actual_detail.display_order`はint unsigned、`t_laser_actual.remarks`はlongtextで、いずれもSELECT・WHEREのどちらでも使わない。

### 34.3 承認済み計画からの逸脱・不確実な点（evaluatorへの確認依頼）

1. **検証項目Aは開発DBで確認済み**。`ai/0056`適用後、`v_ai_laser_production_actual`が31列であること、`pm_ai_reader`で読んだ12,195件が独立JOINの12,195件と一致すること、対象外アクションの行が0件であることを確認した。件数照合テストもスキップせず成功した。
2. **手順SQL（§34.4）は、既存の前例（§33.4等）と同様、`pm_ai_view_owner`への列権限付与・DEFINER付け替えのSQLを用意したが、実行していない**。開発DBで`information_schema.COLUMN_PRIVILEGES`を確認した結果、`pm_ai_view_owner`は`t_laser_actual`・`t_laser_actual_detail`のどの列にもSELECT権限を持っていない(0件)。そのため、§34.4のGRANTは、両テーブルの非公開列(`remarks`・`display_order`)以外の全列が対象になる。
3. **検証項目Kの`makemigrations --dry-run --check`は「No changes detected」、`git diff --check`は成功を確認した**。開発DBには`ai/0056`を適用済み。

### 34.4 手順SQL（`pm_ai_view_owner`への列権限と定義者の付け替え。MySQL固有のため手動。実行はBOSS。`<db>`は接続先のDB名。管理者で実行。`migrate ai 0056`の後）

開発DB確認済み（`information_schema.COLUMN_PRIVILEGES`、2026-10-17）：`pm_ai_view_owner`は`t_laser_actual`・`t_laser_actual_detail`のどの列にもSELECT権限を持っていない（0件）。そのため、非公開列（`t_laser_actual.remarks`・`t_laser_actual_detail.display_order`）以外の全列をGRANTする。

```sql
GRANT SELECT (`id`, `work_date`, `shot_count`, `pattern_no`, `equipment_code`, `equipment_name`, `material_code`, `material_name`, `process_time_per_shot`, `total_process_time`, `created_at`, `updated_at`, `created_by_id`, `equipment_id`, `material_id`, `pattern_id`, `updated_by_id`, `operator_action`, `operator_action_reason`, `line_id`, `process_id`) ON `<db>`.`t_laser_actual` TO 'pm_ai_view_owner'@'localhost';
GRANT SELECT (`id`, `detail_type`, `product_code`, `product_name`, `units_per_shot`, `total_qty`, `created_at`, `updated_at`, `actual_id`, `product_id`, `scrap_qty`, `scrap_reason`) ON `<db>`.`t_laser_actual_detail` TO 'pm_ai_view_owner'@'localhost';
CREATE OR REPLACE DEFINER = 'pm_ai_view_owner'@'localhost' SQL SECURITY DEFINER VIEW `<db>`.`v_ai_laser_production_actual` AS
SELECT
    `d`.`id`,
    `d`.`actual_id`,
    `a`.`created_by_id` AS `operator_user_id`,
    `a`.`equipment_id`,
    `a`.`equipment_code`,
    `a`.`equipment_name`,
    `a`.`line_id`,
    `a`.`process_id`,
    `a`.`pattern_id`,
    `a`.`pattern_no`,
    `a`.`material_id`,
    `a`.`material_code`,
    `a`.`material_name`,
    `d`.`product_id`,
    `d`.`product_code`,
    `d`.`product_name`,
    `a`.`work_date`,
    `a`.`shot_count`,
    `a`.`process_time_per_shot`,
    `a`.`total_process_time`,
    `a`.`operator_action`,
    `a`.`operator_action_reason`,
    `d`.`units_per_shot`,
    `d`.`total_qty`,
    `d`.`scrap_qty`,
    `d`.`scrap_reason`,
    `a`.`updated_by_id` AS `end_operator_user_id`,
    `a`.`created_at` AS `created_at_h`,
    `a`.`updated_at` AS `updated_at_h`,
    `d`.`created_at`,
    `d`.`updated_at`
FROM `<db>`.`t_laser_actual_detail` `d`
JOIN `<db>`.`t_laser_actual` `a` ON `a`.`id` = `d`.`actual_id`
WHERE `a`.`operator_action` IN ('END', 'PAUSE') AND `d`.`detail_type` = 'COMPONENT';
GRANT SELECT ON `<db>`.`v_ai_laser_production_actual` TO 'pm_ai_reader'@'<readerのホスト部>';  -- 開発のreaderがDB全体のSELECTを持つ場合は不要
```

手順SQLのビュー定義は、マイグレーション0056のSELECT（標準SQL）と、列・結合・別名・WHEREが同じであること。

**手順SQLは未実行**（ビュー自体は`ai/0056`で作成済みだが、本節のGRANTと`CREATE OR REPLACE DEFINER`による付け替えは実行していない。実行はBOSS）。

### 34.5 検証結果（generator・evaluatorが実行。開発）

- 開発DBの実データ確認（`SHOW COLUMNS`）：`t_laser_actual`22列・`t_laser_actual_detail`13列。型は§34.1.2の表のとおり実測し、計画の推測値と完全に一致した。
- `line_id`・`process_id`のNULL実態（§34.1.1）：`work_date`が2026-10-12は40件中40件NULL、2026-10-13は45件中45件NULL、2026-10-14は10件中0件NULL、2026-10-15は1件中0件NULL。2026-10-14を境にNULLがゼロになることを確認。
- 独立計算の期待件数（開発DB、`t_laser_actual_detail` JOIN `t_laser_actual` WHERE `operator_action IN ('END','PAUSE')` AND `detail_type='COMPONENT'`）：**12,195件**。
- 開発DBの`django_migrations`で`ai/0056`適用済み。`v_ai_laser_production_actual`は31列で、`pm_ai_reader`による件数12,195件が独立JOINの12,195件と一致し、対象外の`operator_action`は0件。
- `python manage.py test ai.test_analysis_laser_production_actual_view`：**15件成功**。専用モジュールと関連4モジュールの一括実行：**66件成功**。
- `python manage.py makemigrations --dry-run --check`：「No changes detected」。
- `git diff --check`：成功。
- evaluator第1回は、コード・SQLに不合格なし、文書の状態不一致により条件付き。本節とAI用DB辞書の状態を実測結果へ更新した。
- 開発DBのビューの`DEFINER`は`root@localhost`。`pm_ai_view_owner`が元2テーブルに持つ列権限は0件のため、§34.4のowner権限付与・DEFINER付け替え手順は未実施で要対応。

### 34.6 反映状況

- コードを実装し、開発DBへ`ai/0056`を適用済み。`v_ai_laser_production_actual`の作成、31列、`pm_ai_reader`での件数照合まで確認済み。手順SQL（§34.4）は未実行で、定義者は`root@localhost`のまま。
- 評価：evaluator第1回はコード・SQLに不合格なし、文書の状態不一致により条件付き。本修正で実測状態へ更新し、再評価待ち。
- コミット：`d30ab253`で実施済み（AI用ビュー: レーザー生産実績を分析対象に追加）。pushは未実施。
- 未確認・未実施：手順SQL（§34.4）による`pm_ai_view_owner`への元2テーブルの列権限付与とDEFINER付け替え、付け替え後の`pm_ai_reader`再確認、本番反映、push、evaluator再評価。

## 35. ブレーキ・スポット 生産実績のビュー `v_ai_brake_production_actual` の作成前確認・実装記録（2026-10-17。BOSS承認済み。実装済み・evaluator未検証。2026-10-17、BOSS判断により`operator_login_id`・`interruption_reason_code`・`remarks`の3列を追加公開。§35.6参照）

### 35.1 作成前確認

| 確認項目 | 内容 |
|---|---|
| 業務目的 | AIが、ブレーキ・板金スポットの生産実績（作業者アクション・数量・計画日・設備・ライン・工程・品番など）を分析・説明できるようにする |
| 元テーブル | `brake_line_record`（ブレーキライン作業記録）の1つだけ。結合なし（全27,253行。開発DBで確認） |
| 対象行 | 全行（WHEREなし） |
| 数値定義 | `qty`=加工数（`operator_action`がEND・PAUSEの行だけ非ゼロ。START・RESUME・TEMP_ENDは常に0）。`plan_date`=計画日（実列。計算列ではない） |
| 公開フィールド（当初13列。BOSS判断で確定。2026-10-17、BOSS判断により3列追加し16列。§35.6参照） | `id`、`plan_date`、`product_code`、`operator_action`、`operator_action_reason`、`qty`、`sequence_no`、`recorded_at`、`equipment_id`、`line_id`、`process_id`、`product_id`、`operator_user_id`、`operator_login_id`、`interruption_reason_code`、`remarks` |
| 非公開フィールド | `operator`（個人名。`operator_user_id`で代替）のみ |
| 個人情報 | `operator_user_id`は`auth_user.id`へのFK（氏名そのものではない）。氏名そのものの`operator`は非公開 |

#### 35.1.1 列型の対応（`SHOW COLUMNS FROM brake_line_record`。開発DBで実測）

| 列 | MySQL型 | `ANALYSIS_COLUMN_TYPES` |
|---|---|---|
| `id` | bigint | `BIGINT` |
| `plan_date` | date | `DATE` |
| `product_code` | varchar(50) | `VARCHAR` |
| `operator_action` | varchar(20) | `VARCHAR` |
| `operator_action_reason` | varchar(200) | `VARCHAR` |
| `qty` | int | `BIGINT` |
| `sequence_no` | int | `BIGINT` |
| `recorded_at` | datetime(6) | `TIMESTAMP` |
| `equipment_id` | bigint（NULL可） | `BIGINT` |
| `line_id` | bigint | `BIGINT` |
| `process_id` | bigint | `BIGINT` |
| `product_id` | bigint（NULL可） | `BIGINT` |
| `operator_user_id` | int（NULL可） | `BIGINT` |
| `operator_login_id` | varchar(150)（NULL可） | `VARCHAR` |
| `interruption_reason_code` | varchar(4) | `VARCHAR` |
| `remarks` | longtext（NULL可） | `VARCHAR`（§35.6のとおり、`v_ai_process_production_actual`の同種列と同じ扱いでVARCHARとした） |

JSON型の列はない。

#### 35.1.2 実データ確認（開発DB、2026-10-17、generator確認）

- 全件数：27,253件。`line_id`の内訳：`id=9`（`L0010`・ブレーキライン）14,031件、`id=10`（`L0013`・板金スポットライン）13,222件。
- `operator_action`の内訳：START 13,287件、END 13,307件、PAUSE 306件、TEMP_END 61件、RESUME 292件。
- `operator_action_reason`が空文字でないのは PAUSE（306件）・TEMP_END（61件）の行だけ（START・END・RESUME行は常に空文字）。値は固定選択肢（自由記述ではない。例：その他(197)・3S活動(57)・設備トラブル(36)・Khác(27、ベトナム語の「その他」)・機種間違い(24)・治具トラブル(5)・他へ製品切り替え(5)・品番間違い(4)・段取り替え(3)・材料不足(3)・本日設備復旧不可(3)・班長/対応者待ち(2)・Sự cố thiết bị(1、ベトナム語の「設備トラブル」)）。
- `qty`が0でないのは END（12,586件）・PAUSE（208件）の行だけ。START・RESUME・TEMP_ENDは全件`qty=0`。
- `plan_date`と`DATE(recorded_at - INTERVAL 8 HOUR)`が不一致の行：560件（27,253件中2.1%）。算出ロジックの正規仕様は未確認のため、業務日の集計は`plan_date`を正として使う（本仕様書の既存方針どおり、`recorded_at`からの単純な8時間引き算では代替しない）。
- `sequence_no`の内訳：値0は418件（`plan_date`が2026-03-17〜26の9日間に集中。現在のコードに生成経路がなく、過去の一時的事象で業務的意味はない）。値1は26,791件（約98%。通常の計画行に対応）。値2以上は44件（2026-03-24・03-26・04-28・09-15に分散。同一品番・同日に複数の計画行（`LineBacklog`）がある場合の順番を表す）。
- `operator_login_id`：NULLが27,245件（空文字は0件）、値ありは8件。空文字ではなくNULLでほぼ未運用（計画書の見積りは「空文字」としていたが、generator確認の結果はNULL。件数27,245件は一致）。
- `interruption_reason_code`：空文字でないのは4件のみ（PAUSE・TEMP_END合計367件中。いずれもPAUSE行）。
- `remarks`：NULLが27,246件、空文字が7件、それ以外は0件（実質未運用）。

### 35.2 実装内容

- `pm_backend/apps/ai/migrations/0057_ai_brake_production_actual_view.py` 新規。`CREATE OR REPLACE VIEW v_ai_brake_production_actual AS SELECT <13列(2026-10-17に16列へ変更。§35.6参照)> FROM brake_line_record`（標準SQLのみ・別名なし・WHEREなし・結合なし）。ロールバックは`DROP VIEW IF EXISTS v_ai_brake_production_actual`。依存は`ai 0056_ai_laser_production_actual_view`と`production 0121_brakelinerecord_interruption_reason_code_and_more`（`brake_line_record`の列が最後に変わったマイグレーション。実機確認済み：0122〜0124は他モデル（`ProgressMonitorTarget`・`ProcessRealtimeRecord`）の変更で、`BrakeLineRecord`には無関係）。
- `pm_backend/apps/ai/services/sql_queries.py`：`BASE_SQL_SCHEMA`に`v_ai_brake_production_actual`（当初13列。2026-10-17に16列へ変更。§35.6参照。マイグレーションのSELECT順と同じ）を`v_ai_laser_production_actual`の直後に追加。`TABLE_NOTES`にも同じ位置に追加（§35.1.2の実データに基づく内容：`line_id`の区別・`operator_action_reason`が固定選択肢である旨・`qty`の集計方法・`plan_date`と`recorded_at`の不一致率・`sequence_no`の意味）。
- `pm_backend/apps/ai/services/analysis_data_service.py`：`ANALYSIS_VIEWS`に`v_ai_brake_production_actual`（label=ブレーキ・スポット生産実績、`date_field='plan_date'`、`quantity_field='qty'`、説明文）を`v_ai_laser_production_actual`の直後に追加。
- `pm_backend/apps/ai/services/analysis_execution_service.py`：`ANALYSIS_COLUMN_TYPES`に当初13列の型（§35.1.1。2026-10-17に16列へ変更。§35.6参照）を`v_ai_laser_production_actual`の直後に追加。
- `pm_backend/apps/ai/management/commands/setup_ai_views.py`：`SIMPLE_MASTER_VIEWS`に`v_ai_brake_production_actual`→`brake_line_record`を1行追加（結合・WHEREなしの単純なマスタビューのため。既存の`v_ai_equipment`等と同じ扱い）。単純なマスタビューは7つになった。元テーブル`brake_line_record`は、チャットSQL（`ai_home`・`production`画面）向けの`BASE_SQL_SCHEMA`・`PERSONAL_SQL_COLUMNS`・`SCREEN_SQL_TABLES`に既存のエントリ（9列・個人情報`operator`列を含む）を持つが、これは本ビューとは別経路（直接のSQL実行）のため変更していない。
- 試験：`apps/ai/test_analysis_brake_production_actual_view.py`新規（17件。既存の`v_ai_equipment`・`v_ai_laser_production_actual`と同様にSimpleTestCaseで列・型・公開列・非公開列・マイグレーションSQL・`setup_ai_views`登録を検証するテストに加え、開発DBの実テーブルへ直接読み取りだけを行う件数照合テスト、`sequence_no`=0/1/2以上それぞれの件数を検証するテストを追加）。`test_setup_ai_views.py`は`LATEST_MIGRATION`に`v_ai_brake_production_actual`→`0057_ai_brake_production_actual_view.py`を追加。
- 仕様書：本節、`AI運用規約・AI用DB辞書.md`に新規節（§6.5-19）を追加。

### 35.3 承認済み計画からの逸脱・不確実な点（evaluatorへの確認依頼）

1. **`sequence_no=0`の集中期間の記述を、承認済み計画の見積り（「2026-03-18〜26の8日間」）から、generator確認の実データ（2026-03-17〜26の9日間）へ訂正して記載した**。DBを直接確認した結果であり、件数（418件）自体は計画と一致する。
2. **`operator_login_id`の未運用の説明を、承認済み計画の見積り（「空文字」）から、generator確認の実データ（NULLが27,245件、空文字は0件）へ訂正して記載した**。件数（27,245件）自体は計画と一致する。
3. **権限の付与・定義者の付け替えは、`setup_ai_views`（`SIMPLE_MASTER_VIEWS`に追加済み）で行う想定**（`v_ai_equipment`と同じ扱い。§32.2参照）。手動の手順SQLは用意していない（`--apply`の実行は禁止事項のため、generatorは未実施）。
4. **検証項目（件数照合・`sequence_no`バケット照合）は、`migrate`未実行（本ビュー未作成）のため、開発DBの実テーブル直接読み取りによる期待値の確認にとどめ、ビュー自体との照合はスキップ扱いにした**（migrate実行後に有効になる設計。§34のレーザービューと同じ方式）。
5. **検証項目Kの`makemigrations --dry-run --check`は「No changes detected」を確認した**。開発DBには`ai/0057`は未適用（`migrate`は禁止事項のため実施していない）。

### 35.4 検証結果（generatorが実行。開発）

- 開発DBの実データ確認（`SHOW COLUMNS`、件数集計）：§35.1.1・§35.1.2のとおり実測し、計画の推測値とほぼ一致した（`sequence_no=0`の日数・`operator_login_id`の空/NULLの区別のみ、上記§35.3のとおり訂正）。
- `python manage.py test ai.test_analysis_brake_production_actual_view`：**17件成功（うち1件は`migrate`未実行のため意図的にskip）**。
- `ai.test_setup_ai_views ai.test_analysis_equipment_view ai.test_analysis_process_production_actual_view ai.test_analysis_laser_production_actual_view ai.test_analysis_template_review`の一括実行：96件中94件成功・1件は既存の無関係な失敗（`test_analysis_template_review.test_pending_check_happens_inside_the_transaction_after_the_lock_query`。本実装前から存在する既知の食い違いで、本ビューとは無関係。単独実行でも同じ結果になることを確認済み）。
- `ai`アプリ全体（1,150件）の一括実行：1,135件成功・8件failure・7件error・13件skip。失敗・エラーはいずれも本実装（ブレーキビュー・`brake_line_record`関連ファイル）と無関係な既存の食い違い（`test_analysis_user_view`・`test_analysis_bom_item_view`の移行ファイル名の固定値が、`masters`・`accounts`アプリの最新マイグレーションより古いこと、`test_analysis_template_notify`・`test_analysis_template_review`のトランザクション関連、`test_qwen_my_overtime`の外部API依存、`test_analysis_codegen_trial_counts`の無関係な機能）であることを、失敗内容とファイル名で確認した。
- `python manage.py makemigrations --dry-run --check`：「No changes detected」。
- `python manage.py showmigrations ai`：`0057_ai_brake_production_actual_view`が未適用（`[ ]`）であることを確認。

### 35.5 反映状況

- コードを実装（マイグレーション・`sql_queries.py`・`analysis_data_service.py`・`analysis_execution_service.py`・`setup_ai_views.py`・試験2ファイル）。`migrate`・`setup_ai_views --apply`は禁止事項のため未実行。開発DB・本番DBともに`v_ai_brake_production_actual`ビューは未作成。
- 評価：evaluator未検証。
- コミット：未（BOSSの指示後に実施）。
- 未確認・未実施：`migrate ai 0057`の実行、`v_ai_reader`での件数照合（`test_analysis_brake_production_actual_view.BrakeProductionActualDBCountMatchTest.test_view_count_matches_source_table_count`が現在skip）、`setup_ai_views`による権限付与・定義者の付け替え、本番反映、commit・push、evaluator検証。

### 35.6 2026-10-17 BOSS判断による追加公開（`operator_login_id`・`interruption_reason_code`・`remarks`を非公開→公開）

- BOSSが当初非公開としていた3列（`operator_login_id`・`interruption_reason_code`・`remarks`）を公開に変更すると決定した。
- **事実誤認の訂正（2026-10-18、evaluator指摘により判明）**: 当初、`0057_ai_brake_production_actual_view.py`のSELECT文を直接書き換える対応を行ったが、実際には**0057は既に開発DBへ`migrate`適用済み**（適用日時2026-10-17 21:19:25。コミット`1498f72a`で13列版として確定済み）だった。Djangoは適用済みマイグレーションのSQL内容を変更しても再実行しないため、ファイルを直接書き換えても開発DBのビュー定義（13列のまま）には反映されず、新3列を参照するクエリが`Unknown column`エラーになる不整合が発生していた。
- **対応**: `0057_ai_brake_production_actual_view.py`を元の13列版（コミット`1498f72a`の内容）に復元し、新規マイグレーション`0059_ai_brake_production_actual_view_add_columns.py`を追加して、そちらで16列版の`CREATE OR REPLACE VIEW`を再発行する方式に変更した。依存は`ai 0057`・`ai 0058`（レーザー中断ビュー、他セッション作成・2026-10-18時点で未コミット）。`python manage.py makemigrations --dry-run --check`で「No changes detected」を確認済み。開発DBへの`migrate`再実行はBOSSが行う。
- 公開列は13列→16列（列順は§35.1の表のとおり。末尾に3列を追加）。非公開は`operator`（個人名）のみになった。
- `remarks`の実際のDB型は`SHOW COLUMNS FROM brake_line_record`で`longtext`（NULL可）と確認した（`varchar`ではない）。`ANALYSIS_COLUMN_TYPES`では、既存の`v_ai_process_production_actual`の同種列（`remarks`）と同じ扱いで`VARCHAR`とした（longtext・varcharいずれも`ANALYSIS_COLUMN_TYPES`では`VARCHAR`で統一する既存方針に合わせた）。
- 開発DB実データ再確認（2026-10-17）：全27,253件。`operator_login_id`はNULLが27,245件（値ありは8件、§35.1.2と同じ）。`interruption_reason_code`は値ありが4件（PAUSE・TEMP_END合計367件中。§35.1.2と同じ）。`remarks`は値ありが0件（空文字含め全件NULLまたは空、実質未運用）。3列とも「現状ほぼ未運用だが今後のデータ蓄積を見込んで公開」という趣旨をコード中のコメント・`TABLE_NOTES`・`ANALYSIS_VIEWS`の説明文に記載した。
- 変更ファイル：`pm_backend/apps/ai/migrations/0057_ai_brake_production_actual_view.py`（SELECT句・コメント）、`pm_backend/apps/ai/services/sql_queries.py`（`BASE_SQL_SCHEMA`・`TABLE_NOTES`・コメント）、`pm_backend/apps/ai/services/analysis_data_service.py`（`ANALYSIS_VIEWS`の説明文）、`pm_backend/apps/ai/services/analysis_execution_service.py`（`ANALYSIS_COLUMN_TYPES`）、`pm_backend/apps/ai/test_analysis_brake_production_actual_view.py`（`PUBLISHED`・`HIDDEN`・列数・型辞書・説明文アサーションを16列公開の前提に更新）。`setup_ai_views.py`は`wanted_columns()`が`BASE_SQL_SCHEMA`から動的に算出するため変更不要（確認済み）。
- 検証結果：`python manage.py test ai.test_analysis_brake_production_actual_view` 15件成功（3列公開に合わせてテストの列数・型辞書・HIDDENタプルを更新したため、総件数は17件→15件に変化。`test_validate_datasets_requires_plan_date_and_rejects_hidden_columns`が非公開列でループする対象が`operator`の1件のみになったため）。`python manage.py makemigrations --dry-run --check`は「No changes detected」（本変更はSQLのみでモデル変更を伴わないため）。
- 反映状況：コードのみ変更。`migrate`・`setup_ai_views --apply`・コミット・pushは未実施（禁止事項のため）。開発DB・本番DBともに`v_ai_brake_production_actual`ビューは未作成のまま。evaluator未検証。

## 36. レーザー 中断のビュー `v_ai_laser_interruption` の作成前確認・実装記録（2026-10-17。BOSS承認済み。実装済み・evaluator未検証）

### 36.1 作成前確認

| 確認項目 | 内容 |
|---|---|
| 業務目的 | AIが、レーザーの中断（中断発生時のライン・工程・パターン・使用材料・作業者アクションなど）を分析・説明できるようにする |
| 元テーブル | `t_laser_actual`単独（結合なし）。`t_laser_actual_detail`へは結合しない（結合すると中断1件が明細の行数分重複するため、BOSSが結合なし設計を決定済み） |
| 対象行 | `WHERE operator_action IN ('PAUSE', 'TEMP_END')`（中断・強制終了の行だけ） |
| 数値定義 | 数量の列はなし（`quantity_field=None`）。`work_date`=作業日（実列、計算列ではない） |
| 公開フィールド（15列。BOSS判断で確定） | `id`、`work_date`、`equipment_id`、`equipment_code`、`equipment_name`、`line_id`、`process_id`、`pattern_no`、`material_id`、`material_code`、`material_name`、`operator_action`、`operator_action_reason`、`operator_user_id`（`created_by_id`の別名）、`created_at` |
| 非公開フィールド | `t_laser_actual_detail`側の列（`detail_product_code`・`detail_total_qty`相当の情報）は、結合しない設計のため構造的に出現しない（非公開列を個別に定める必要はない） |
| 個人情報 | `operator_user_id`は`auth_user.id`へのFK（氏名そのものではない）。既存の`v_ai_laser_production_actual`と同様、本ビューはIDだけを公開し、氏名は公開しない |

#### 36.1.1 開発DBの実データ確認（2026-10-17、generator確認）

- `operator_action`の内訳（ヘッダ単位、重複なし）：PAUSE 16件、TEMP_END 0件、合計16件。
- `work_date`の範囲：2026-05-25〜2026-10-09（全16件が2026-10-14より前）。
- `line_id`・`process_id`がNOT NULLの行：0件（16件全件がNULL）。2026-10-14にライン・工程の保存機能を追加した（`production/migrations/0118_laser_actual_line_process.py`）ため、それより前の実績行はNULLになる仕様（`v_ai_laser_production_actual`・計画書 §34.1.1と同じ事実）。本ビューの対象16件は全件がこの保存機能追加前の実績のため、現時点では全件NULLになる。将来2026-10-14以降のPAUSE・TEMP_ENDが発生すれば値が入る。
- `material_id`がNULLの行：0件（16件全件で値あり）。
- `equipment_id`がNULLの行：0件（16件全件で値あり）。
- `created_by_id`（`operator_user_id`）がNULLの行：0件（16件全件で値あり）。

#### 36.1.2 列型の対応（`SHOW COLUMNS FROM t_laser_actual`。開発DBで実測）

| 列 | 元テーブル・MySQL型 | `ANALYSIS_COLUMN_TYPES` |
|---|---|---|
| `id` | `bigint` | `BIGINT` |
| `work_date` | `date` | `DATE` |
| `equipment_id` | `bigint` | `BIGINT` |
| `equipment_code` | `varchar(50)` | `VARCHAR` |
| `equipment_name` | `varchar(100)` | `VARCHAR` |
| `line_id` | `bigint`、NULL可 | `BIGINT` |
| `process_id` | `bigint`、NULL可 | `BIGINT` |
| `pattern_no` | `varchar(50)` | `VARCHAR` |
| `material_id` | `bigint`、NULL可 | `BIGINT` |
| `material_code` | `varchar(50)` | `VARCHAR` |
| `material_name` | `varchar(100)` | `VARCHAR` |
| `operator_action` | `varchar(20)` | `VARCHAR` |
| `operator_action_reason` | `varchar(200)` | `VARCHAR` |
| `operator_user_id` | `created_by_id`、`int`、NULL可 | `BIGINT` |
| `created_at` | `datetime(6)` | `TIMESTAMP` |

参考（本ビューでは参照しない。`t_laser_actual_detail`の列。結合しないため構造的に出現しない）：`detail_product_code`・`detail_total_qty`相当の情報（構成部品・生産数量）は、本ビューには出ない。生産数量を見たいときは`v_ai_laser_production_actual`（§34）を使う。

### 36.2 実装内容

- 新規 `pm_backend/apps/ai/migrations/0058_ai_laser_interruption_view.py`。`CREATE OR REPLACE VIEW v_ai_laser_interruption AS SELECT <15列> FROM t_laser_actual WHERE operator_action IN ('PAUSE', 'TEMP_END')`（標準SQLのみ・バッククォート/DEFINER/SQL SECURITY/DB修飾なし・結合なし）。ロールバックは`DROP VIEW IF EXISTS v_ai_laser_interruption`。依存は`ai 0057_ai_brake_production_actual_view`と`production 0118_laser_actual_line_process`（`line_id`・`process_id`列の追加マイグレーション。`v_ai_laser_production_actual`と同じ依存）。
- `pm_backend/apps/ai/services/sql_queries.py`：`BASE_SQL_SCHEMA`に`v_ai_laser_interruption`（15列。マイグレーションのSELECT順と同じ）を`v_ai_brake_production_actual`の直後に追加。`TABLE_NOTES`にも同じ位置に追加（§36.1・§36.1.1の内容。結合なし設計の理由、`line_id`・`process_id`が2026-10-14より前はNULLになる旨、現在の対象16件全件がNULLである旨、`operator_user_id`が`created_by_id`の別名である旨を明記）。
- `pm_backend/apps/ai/services/analysis_data_service.py`：`ANALYSIS_VIEWS`に`v_ai_laser_interruption`（label=レーザー中断、`date_field='work_date'`、`quantity_field=None`、説明文）を`v_ai_brake_production_actual`の直後に追加。
- `pm_backend/apps/ai/services/analysis_execution_service.py`：`ANALYSIS_COLUMN_TYPES`に15列の型（§36.1.2）を`v_ai_brake_production_actual`の直後に追加。
- `pm_backend/apps/ai/management/commands/setup_ai_views.py`：`EXISTING_JOIN_VIEWS`に`v_ai_laser_interruption`を追加（単一テーブルでもWHERE句で絞り込むため`SIMPLE_MASTER_VIEWS`ではなく、既存の`v_ai_laser_production_actual`等と同じ「結合・WHERE句あり」の扱い。再作成しない。`--check`で定義者等を表示するだけ）。近くのコメントの対象マイグレーション番号の一覧に`0058`を追記。`SIMPLE_MASTER_VIEWS`・`OTHER_VIEW_COLUMNS`は変更していない（`t_laser_actual`は他の公開ビューと列を共有しないため）。
- 試験：`apps/ai/test_analysis_laser_interruption_view.py`新規（16件。既存の`v_ai_laser_production_actual`・`v_ai_brake_production_actual`と同様にSimpleTestCaseで列・型・公開列・マイグレーションSQL・`setup_ai_views`登録を検証するテストに加え、開発DBの実テーブルへ直接読み取りだけを行う件数照合テスト、`operator_action`別（PAUSE・TEMP_END）の件数を検証するテストを追加）。
- 仕様書：本節、`AI運用規約・AI用DB辞書.md`に新規節（§6.5-20）を追加。

### 36.3 承認済み計画からの逸脱・不確実な点（evaluatorへの確認依頼）

1. **承認済み計画の時点で想定していたマイグレーション番号は0058だったが、並行実装（§35のブレーキビュー）が先に0057を使ったため、実際の番号もちょうど0058のままで一致した**（確認した上での一致。ズレはなかった）。
2. **検証項目（件数照合・operator_action別の件数照合）は、`migrate`未実行（本ビュー未作成）のため、開発DBの実テーブル直接読み取りによる期待値の確認にとどめ、ビュー自体との照合はスキップ扱いにした**（migrate実行後に有効になる設計。§34・§35と同じ方式）。
3. **権限の付与・定義者の付け替えは、既存の`v_ai_laser_production_actual`と同様、手動の手順SQLが必要な想定だが、本節では手順SQLを作成していない**（`EXISTING_JOIN_VIEWS`は`--check`で定義者等を表示するだけのため。必要であれば別途BOSSの指示で作成する）。
4. **検証項目の`makemigrations --dry-run --check`は「No changes detected」を確認した**。
5. **generatorの実装完了後、本セッション中に`ai/0058`が開発DBへ適用された（`showmigrations ai`で`[X]`に変化、`v_ai_laser_interruption`ビューが実在することを確認）**。generator自身は`migrate`を実行していない（禁止事項のため）。BOSSまたは他の作業（並行していたブレーキビューの作業）の中で適用されたと見られるが、実行者・実行コマンドはgeneratorからは確認できない。結果として、件数照合テストが実際のビューに対して実行され、スキップされずに成功した（§36.4）。

### 36.4 検証結果（generatorが実行。開発）

- 開発DBの実データ確認（`SHOW COLUMNS`、件数集計）：§36.1.1・§36.1.2のとおり実測し、承認済み計画の推測値（PAUSE16件・TEMP_END0件、line_id・process_id全件NULL、material_id・equipment_id・operator_user_id全件値あり）と完全に一致した。
- `python manage.py test ai.test_analysis_laser_interruption_view`：当初（migrate未適用時点）は**16件中15件成功・1件skip**。その後`ai/0058`が開発DBへ適用されたため再実行し、**16件全件成功（skipなし）**。件数照合テスト（`LaserInterruptionDBCountMatchTest.test_view_count_matches_independent_count`）が実際に`SELECT COUNT(*) FROM v_ai_laser_interruption`を実行し、独立計算の16件と一致することを確認した。
- `ai.test_setup_ai_views ai.test_analysis_laser_production_actual_view ai.test_analysis_brake_production_actual_view ai.test_analysis_laser_interruption_view`の一括実行（migrate未適用時点）：67件成功（skip1件）。
- `ai`アプリ全体（1,166件）の一括実行（migrate未適用時点）：1,150件成功・8件failure・7件error・13件skip（新規追加16件を含む）。失敗・エラーの内容は§35.4で確認済みの既存の無関係な食い違い（`test_analysis_user_view`・`test_analysis_bom_item_view`の移行ファイル名の固定値、`test_analysis_template_notify`・`test_analysis_template_review`のトランザクション関連、`test_qwen_my_overtime`の外部API依存、`test_analysis_codegen_trial_counts`の無関係な機能）と同一であることをテスト名で確認した（本実装による新規の失敗・エラーはない）。
- 別途、`ai/0058`適用後に`ai.test_setup_ai_views`を単独再実行したところ、ブレーキビュー側の並行作業（`0059_ai_brake_production_actual_view_add_columns`マイグレーション追加と`BASE_SQL_SCHEMA['v_ai_brake_production_actual']`の列追加が、`test_setup_ai_views.LATEST_MIGRATION`の対応付け未更新と食い違ったため）で`test_migration_columns_match_command`が1件失敗した。これはブレーキビューの並行作業に起因し、本実装（レーザー中断）の変更範囲外のため、generatorでは修正していない。
- `python manage.py makemigrations --dry-run --check`：「No changes detected」（ブレーキビューの並行作業によるマイグレーション追加後も再確認し、同じ結果）。
- `python manage.py showmigrations ai`：実装直後は`0058_ai_laser_interruption_view`が未適用（`[ ]`）だったが、その後`[X]`（適用済み）に変化したことを確認した（§36.3-5）。

### 36.5 反映状況

- コードを実装（マイグレーション・`sql_queries.py`・`analysis_data_service.py`・`analysis_execution_service.py`・`setup_ai_views.py`・試験1ファイル）。generator自身は`migrate`・`setup_ai_views --apply`を実行していない（禁止事項のため）。
- **開発DBの状態（2026-10-18確認）**：`ai/0058`は適用済み（`showmigrations`で`[X]`）。`v_ai_laser_interruption`ビューが実在し、15列・16行（`SHOW COLUMNS`・`SELECT COUNT(*)`で確認）。本番DBは未反映。
- 評価：evaluator未検証。
- コミット：未（BOSSの指示後に実施）。
- 未確認・未実施：`setup_ai_views`による権限付与・定義者の付け替え（手順SQLも未作成。現在のDEFINERは`root@localhost`と推定されるが、generatorは`information_schema`での確認を今回は実施していない）、本番反映、commit・push、evaluator検証。並行していたブレーキビュー（§35）側の`test_setup_ai_views`不整合（上記36.4）の解消は、本実装の範囲外のためBOSSまたはブレーキビュー担当へ報告が必要。
